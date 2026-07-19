"""Application entrypoint for pothole dashcam service."""

from __future__ import annotations

import logging
from pathlib import Path

from pothole_dashcam.services.camera_buffer_service import CameraBufferService
from pothole_dashcam.services.camera_service import StubCameraService, UsbCameraService
from pothole_dashcam.services.event_consumer import StubEventConsumer
from pothole_dashcam.services.inference_service import StubInferenceService
from pothole_dashcam.services.upload_service import StubUploadService


def bootstrap() -> None:
    """Initialize minimal runtime dependencies for local execution."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    # Dependency placeholders to unblock teammate parallel work.
    _ = StubEventConsumer()
    _ = StubCameraService()
    _ = StubInferenceService()
    _ = StubUploadService()

    frame_buffer = CameraBufferService(
        db_path=Path("runtime/frame_index.db"),
        image_dir=Path("runtime/frames"),
        retention_minutes=10,
        max_frames=600,
    )

    # Optional hardware smoke: capture one live frame if USB camera is available.
    try:
        usb_camera = UsbCameraService(device_index=0)
        frame_ref = frame_buffer.capture_once(usb_camera.capture_jpeg_bytes())
        usb_camera.close()
        logging.getLogger(__name__).info("captured frame: %s", frame_ref.path)
    except RuntimeError as exc:
        logging.getLogger(__name__).warning("camera smoke capture skipped: %s", exc)

    frame_buffer.close()
    logging.getLogger(__name__).info("pothole_dashcam bootstrap complete")


def main() -> None:
    """CLI entrypoint."""
    bootstrap()


if __name__ == "__main__":
    main()
