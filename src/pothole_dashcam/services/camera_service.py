"""Camera service contract and USB camera implementation."""

from __future__ import annotations

from types import ModuleType
from typing import Protocol

from pothole_dashcam.models import Event, FrameRef


class CameraService(Protocol):
    """Contract for retrieving frames around a trigger event."""

    def get_frames_for_event(self, event: Event) -> list[FrameRef]:
        """Return frame references used for pothole confirmation."""
        ...


class UsbCameraService:
    """V4L2/OpenCV-backed USB camera capture service for Linux targets."""

    def __init__(self, device_index: int = 0) -> None:
        """Open a camera device index and prepare it for frame capture."""
        try:
            import cv2  # pylint: disable=import-outside-toplevel
        except ImportError as exc:  # pragma: no cover - hardware/runtime dependency
            msg = "opencv-python-headless is required for UsbCameraService"
            raise RuntimeError(msg) from exc

        self._cv2: ModuleType = cv2
        self._cap = cv2.VideoCapture(device_index)
        if not self._cap.isOpened():
            msg = f"unable to open camera device index {device_index}"
            raise RuntimeError(msg)

    def close(self) -> None:
        """Release camera device handle."""
        self._cap.release()

    def capture_jpeg_bytes(self) -> bytes:
        """Capture one frame and encode as JPEG bytes."""
        success, frame = self._cap.read()
        if not success:
            msg = "camera frame capture failed"
            raise RuntimeError(msg)

        ok, encoded = self._cv2.imencode(".jpg", frame)
        if not ok:
            msg = "camera frame JPEG encoding failed"
            raise RuntimeError(msg)

        return bytes(encoded)


class StubCameraService:
    """Placeholder camera service used during initial bootstrap."""

    def get_frames_for_event(self, event: Event) -> list[FrameRef]:
        _ = event
        return []
