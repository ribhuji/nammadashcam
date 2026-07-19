"""Application entrypoint for pothole dashcam service."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pothole_dashcam.services.camera_buffer_service import CameraBufferService
from pothole_dashcam.services.camera_service import StubCameraService, UsbCameraService
from pothole_dashcam.services.capture_loop_service import CaptureLoopService
from pothole_dashcam.services.event_consumer import StubEventConsumer
from pothole_dashcam.services.inference_service import (
    OnnxPotholeInferenceService,
    StubInferenceService,
)
from pothole_dashcam.services.upload_service import StubUploadService

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse runtime CLI options for backend selection."""
    parser = argparse.ArgumentParser(description="Pothole dashcam bootstrap")
    parser.add_argument(
        "--camera-backend",
        choices=("stub", "usb"),
        default="stub",
        help="Camera backend to initialize (default: stub)",
    )
    parser.add_argument(
        "--camera-device-index",
        type=int,
        default=0,
        help="Video device index for USB camera backend (default: 0)",
    )
    parser.add_argument(
        "--inference-backend",
        choices=("stub", "onnx"),
        default="stub",
        help="Inference backend to initialize (default: stub)",
    )
    parser.add_argument(
        "--onnx-model-path",
        type=Path,
        default=Path("models/best.onnx"),
        help="Path to ONNX model file when inference backend is onnx",
    )
    parser.add_argument(
        "--inference-threshold",
        type=float,
        default=0.5,
        help="Confidence threshold for pothole classification (default: 0.5)",
    )
    parser.add_argument(
        "--capture-interval-s",
        type=float,
        default=1.0,
        help="Capture interval in seconds for continuous loop (default: 1.0)",
    )
    parser.add_argument(
        "--capture-max-frames",
        type=int,
        default=0,
        help="Optional frame limit for one run (0 means unbounded)",
    )
    parser.add_argument(
        "--capture-max-seconds",
        type=float,
        default=0.0,
        help="Optional duration limit in seconds for one run (0 means unbounded)",
    )
    return parser.parse_args()


def bootstrap(
    camera_backend: str,
    camera_device_index: int,
    inference_backend: str,
    onnx_model_path: Path,
    inference_threshold: float,
    capture_interval_s: float,
    capture_max_frames: int,
    capture_max_seconds: float,
) -> None:
    """Initialize runtime dependencies and start continuous capture pipeline."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    # Dependency placeholders to unblock teammate parallel work.
    _ = StubEventConsumer()
    _ = StubUploadService()

    frame_buffer = CameraBufferService(
        db_path=Path("runtime/frame_index.db"),
        image_dir=Path("runtime/frames"),
        retention_minutes=10,
        max_frames=600,
    )

    camera_handle: UsbCameraService | StubCameraService
    if camera_backend == "usb":
        camera_handle = UsbCameraService(device_index=camera_device_index)
        LOGGER.info("initialized USB camera backend on /dev/video%s", camera_device_index)
    else:
        camera_handle = StubCameraService()
        LOGGER.info("initialized stub camera backend")

    max_frames_arg: int | None = capture_max_frames if capture_max_frames > 0 else None
    max_seconds_arg: float | None = capture_max_seconds if capture_max_seconds > 0.0 else None
    capture_loop = CaptureLoopService(
        camera_service=camera_handle,
        frame_buffer=frame_buffer,
        capture_interval_s=capture_interval_s,
    )

    if inference_backend == "onnx":
        if not onnx_model_path.exists():
            LOGGER.warning(
                "ONNX model not found at %s; falling back to stub inference backend",
                onnx_model_path,
            )
            inference_handle = StubInferenceService()
            LOGGER.info("initialized stub inference backend")
        else:
            inference_handle = OnnxPotholeInferenceService(
                model_path=onnx_model_path,
                confidence_threshold=inference_threshold,
            )
            LOGGER.info(
                "initialized ONNX inference backend with model %s",
                onnx_model_path,
            )
    else:
        inference_handle = StubInferenceService()
        LOGGER.info("initialized stub inference backend")

    _ = inference_handle

    captured = 0
    try:
        captured = capture_loop.run(max_captures=max_frames_arg, max_duration_s=max_seconds_arg)
        LOGGER.info("capture loop completed, frames captured=%s", captured)
        LOGGER.info("frame buffer count=%s", frame_buffer.frame_count())
    finally:
        camera_handle.close()
        frame_buffer.close()

    LOGGER.info("pothole_dashcam bootstrap complete")


def main() -> None:
    """CLI entrypoint."""
    args = parse_args()
    bootstrap(
        camera_backend=args.camera_backend,
        camera_device_index=args.camera_device_index,
        inference_backend=args.inference_backend,
        onnx_model_path=args.onnx_model_path,
        inference_threshold=args.inference_threshold,
        capture_interval_s=args.capture_interval_s,
        capture_max_frames=args.capture_max_frames,
        capture_max_seconds=args.capture_max_seconds,
    )


if __name__ == "__main__":
    main()
