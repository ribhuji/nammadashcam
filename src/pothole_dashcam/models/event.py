"""Core event and result models for service contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Event:
    """Trigger event from the accelerometer integration layer."""

    event_id: str
    timestamp_ms: int
    severity: float
    source: str


@dataclass(frozen=True)
class FrameRef:
    """Reference to a captured frame artifact."""

    frame_id: str
    path: str
    timestamp_ms: int


@dataclass(frozen=True)
class InferenceResult:
    """Inference outcome for pothole confirmation."""

    is_pothole: bool
    confidence: float
    label: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UploadResult:
    """Cloud upload result status."""

    uploaded: bool
    remote_url: str | None
    retryable_error: str | None
