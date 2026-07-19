"""Application entrypoint for pothole dashcam service."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pothole_dashcam.services.camera_buffer_service import CameraBufferService
from pothole_dashcam.services.camera_service import StubCameraService, UsbCameraService
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
    return parser.parse_args()


def bootstrap(
    camera_backend: str,
    camera_device_index: int,
    inference_backend: str,
    onnx_model_path: Path,
    inference_threshold: float,
) -> None:
    """Initialize runtime dependencies with selected camera and inference backends."""
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
        camera_handle.close()
    else:
        camera_handle = StubCameraService()
        LOGGER.info("initialized stub camera backend")

    _ = camera_handle

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

    # Runtime frame buffer is created at bootstrap; capture loop runs in service phase.
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
    )


if __name__ == "__main__":
    main()
