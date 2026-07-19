"""Data models used across services."""

from pothole_dashcam.models.event import Event, FrameRef, InferenceResult, UploadResult
from pothole_dashcam.models.movement import MovementEvent

__all__ = [
    "Event",
    "FrameRef",
    "InferenceResult",
    "MovementEvent",
    "UploadResult",
]
