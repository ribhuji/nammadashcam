"""Tests for ONNX pothole inference service behavior."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

from pothole_dashcam.models import FrameRef
from pothole_dashcam.services.inference_service import OnnxPotholeInferenceService


class _FakeSession:
    def __init__(self, output: np.ndarray) -> None:
        self._output = output

    def get_inputs(self) -> list[object]:
        class _Input:
            name = "images"

        return [_Input()]

    def run(self, _unused: object, _feed: object) -> list[np.ndarray]:
        return [self._output]


class _FakeOrt(ModuleType):
    def __init__(self, output: np.ndarray) -> None:
        super().__init__("onnxruntime")
        self._output = output

    def InferenceSession(self, _path: str, providers: list[str]) -> _FakeSession:  # noqa: N802
        _ = providers
        return _FakeSession(output=self._output)


class _FakeCv2(ModuleType):
    COLOR_BGR2RGB = 4

    def __init__(self, image: np.ndarray) -> None:
        super().__init__("cv2")
        self._image = image

    def imread(self, _path: str) -> np.ndarray | None:
        return self._image

    def resize(self, image: np.ndarray, _size: tuple[int, int]) -> np.ndarray:
        return image

    def cvtColor(self, image: np.ndarray, _code: int) -> np.ndarray:  # noqa: N802
        return image


def test_infer_image_path_positive_detection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Service should mark pothole true when confidence exceeds threshold."""
    output = np.zeros((1, 5, 10), dtype=np.float32)
    output[0, 4, 3] = 0.8

    monkeypatch.setitem(sys.modules, "onnxruntime", _FakeOrt(output=output))
    monkeypatch.setitem(sys.modules, "cv2", _FakeCv2(image=np.ones((640, 640, 3), dtype=np.uint8)))

    service = OnnxPotholeInferenceService(
        model_path=tmp_path / "best.onnx",
        confidence_threshold=0.5,
    )

    result = service.infer_image_path(tmp_path / "img.jpg")

    assert result.is_pothole
    assert result.label == "pothole"
    assert result.confidence == pytest.approx(0.8, rel=1e-6)


def test_confirm_pothole_uses_latest_frame(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """List-based contract should select latest timestamp frame."""
    output = np.zeros((1, 5, 10), dtype=np.float32)
    output[0, 4, 1] = 0.6

    monkeypatch.setitem(sys.modules, "onnxruntime", _FakeOrt(output=output))
    monkeypatch.setitem(sys.modules, "cv2", _FakeCv2(image=np.ones((640, 640, 3), dtype=np.uint8)))

    service = OnnxPotholeInferenceService(
        model_path=tmp_path / "best.onnx",
        confidence_threshold=0.5,
    )

    frames = [
        FrameRef(frame_id="1", path=str(tmp_path / "a.jpg"), timestamp_ms=1000),
        FrameRef(frame_id="2", path=str(tmp_path / "b.jpg"), timestamp_ms=2000),
    ]
    result = service.confirm_pothole(frames)

    assert result.is_pothole
    assert result.confidence == pytest.approx(0.6, rel=1e-6)


def test_confirm_pothole_empty_frames_returns_no_frames(tmp_path: Path) -> None:
    """Empty frame list should return deterministic no-frame response."""
    service = object.__new__(OnnxPotholeInferenceService)
    result = service.confirm_pothole([])

    assert not result.is_pothole
    assert result.label == "no_frames"
    assert result.metadata["reason"] == "empty_frame_list"


@pytest.mark.skipif(
    os.getenv("RUN_ONNX_REAL_TEST") != "1",
    reason="set RUN_ONNX_REAL_TEST=1 and provide test ONNX model to run",
)
def test_real_onnx_model_on_sample_pothole_image() -> None:
    """Run real ONNX inference on bundled pothole sample image.

    This test is opt-in so teammates without model files can still run the
    normal test suite.
    """
    model_path = Path("models/best.onnx")
    image_path = Path("tests/assets/pothole_sample.jpg")

    assert model_path.exists(), "models/best.onnx not found"
    assert image_path.exists(), "tests/assets/pothole_sample.jpg not found"

    service = OnnxPotholeInferenceService(model_path=model_path, confidence_threshold=0.5)
    result = service.infer_image_path(image_path)

    assert result.label in {"pothole", "no_pothole"}
    assert 0.0 <= result.confidence <= 1_000_000.0
    assert "model_path" in result.metadata
