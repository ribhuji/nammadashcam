"""Camera service contract and placeholder implementation."""

from __future__ import annotations

from typing import Protocol

from pothole_dashcam.models import Event, FrameRef


class CameraService(Protocol):
    """Contract for retrieving frames around a trigger event."""

    def get_frames_for_event(self, event: Event) -> list[FrameRef]:
        """Return frame references used for pothole confirmation."""
        ...


class StubCameraService:
    """Placeholder camera service used during initial bootstrap."""

    def get_frames_for_event(self, event: Event) -> list[FrameRef]:
        _ = event
        return []
