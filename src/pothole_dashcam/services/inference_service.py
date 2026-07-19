"""Inference service contract and ONNX-based pothole implementation."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Protocol

from pothole_dashcam.models import FrameRef, InferenceResult


class InferenceService(Protocol):
    """Contract for classifying frames for pothole evidence."""

    def confirm_pothole(self, frames: list[FrameRef]) -> InferenceResult:
        """Return inference result based on provided frames."""
        ...


class OnnxPotholeInferenceService:
    """Run pothole detection using ONNX Runtime on image file paths."""

    def __init__(
        self,
        model_path: str | Path,
        confidence_threshold: float = 0.5,
        input_size: int = 640,
    ) -> None:
        """Create ONNX runtime session and store preprocessing config."""
        if confidence_threshold < 0.0 or confidence_threshold > 1.0:
            msg = "confidence_threshold must be between 0.0 and 1.0"
            raise ValueError(msg)

        if input_size <= 0:
            msg = "input_size must be > 0"
            raise ValueError(msg)

        self._model_path = Path(model_path)
        self._confidence_threshold = confidence_threshold
        self._input_size = input_size

        try:
            import cv2  # pylint: disable=import-outside-toplevel
            import numpy as np  # pylint: disable=import-outside-toplevel
            import onnxruntime as ort  # pylint: disable=import-outside-toplevel
        except ImportError as exc:  # pragma: no cover - runtime dependency on target
            msg = "opencv-python-headless, numpy, and onnxruntime are required"
            raise RuntimeError(msg) from exc

        self._cv2: ModuleType = cv2
        self._np: ModuleType = np
        self._ort: ModuleType = ort
        self._session = ort.InferenceSession(
            str(self._model_path),
            providers=["CPUExecutionProvider"],
        )
        inputs = self._session.get_inputs()
        if not inputs:
            msg = "onnx model has no input tensors"
            raise RuntimeError(msg)
        self._input_name = str(inputs[0].name)

    def infer_image_path(self, image_path: str | Path) -> InferenceResult:
        """Infer pothole presence from one image path."""
        image = self._cv2.imread(str(image_path))
        if image is None:
            msg = f"unable to read image: {image_path}"
            raise RuntimeError(msg)

        resized = self._cv2.resize(image, (self._input_size, self._input_size))
        rgb = self._cv2.cvtColor(resized, self._cv2.COLOR_BGR2RGB)

        tensor = rgb.astype(self._np.float32) / 255.0
        tensor = self._np.transpose(tensor, (2, 0, 1))[None, ...]

        output = self._session.run(None, {self._input_name: tensor})
        if not output:
            msg = "onnx inference returned no outputs"
            raise RuntimeError(msg)

        confidence = self._extract_confidence(output[0])
        is_pothole = confidence >= self._confidence_threshold

        return InferenceResult(
            is_pothole=is_pothole,
            confidence=confidence,
            label="pothole" if is_pothole else "no_pothole",
            metadata={
                "model_path": str(self._model_path),
                "input_name": self._input_name,
                "threshold": self._confidence_threshold,
            },
        )

    def confirm_pothole(self, frames: list[FrameRef]) -> InferenceResult:
        """Infer from latest frame in a list-based pipeline contract."""
        if not frames:
            return InferenceResult(
                is_pothole=False,
                confidence=0.0,
                label="no_frames",
                metadata={"reason": "empty_frame_list"},
            )

        # Use most recent frame by timestamp as representative evidence.
        latest = max(frames, key=lambda frame: frame.timestamp_ms)
        return self.infer_image_path(latest.path)

    def _extract_confidence(self, model_output: object) -> float:
        """Extract best confidence from YOLO-like model output tensor."""
        output = self._np.asarray(model_output)
        if output.size == 0:
            return 0.0

        # Expected one-class layout from current exported model: (1, 5, N).
        if output.ndim == 3 and output.shape[1] >= 5:
            conf_row = output[0, 4, :]
            return float(self._np.max(conf_row))

        # Fallback for unknown layout: use maximum activation as proxy.
        return float(self._np.max(output))


class StubInferenceService:
    """Placeholder inference service for bootstrap stage."""

    def confirm_pothole(self, frames: list[FrameRef]) -> InferenceResult:
        _ = frames
        return InferenceResult(
            is_pothole=False,
            confidence=0.0,
            label="unknown",
            metadata={},
        )
