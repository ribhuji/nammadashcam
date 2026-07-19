"""Application entrypoint for pothole dashcam service."""

from __future__ import annotations

import logging

from pothole_dashcam.services.camera_service import StubCameraService
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

    logging.getLogger(__name__).info("pothole_dashcam bootstrap complete")


def main() -> None:
    """CLI entrypoint."""
    bootstrap()


if __name__ == "__main__":
    main()
