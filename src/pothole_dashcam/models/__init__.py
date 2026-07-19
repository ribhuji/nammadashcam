"""Data models used across services."""

from pothole_dashcam.models.event import Event, FrameRef, InferenceResult, UploadResult

__all__ = [
    "Event",
    "FrameRef",
    "InferenceResult",
    "UploadResult",
]
