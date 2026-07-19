"""Movement-sidecar event models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class MovementEvent:
    """Slim normalized movement event derived from MCU serial payloads."""

    event_id: int
    arduino_timestamp_ms: int
    received_monotonic_ms: int
    severity: float
    confidence: float
    window_pre_ms: int
    window_post_ms: int
    raw_payload: Mapping[str, Any] = field(default_factory=dict, repr=False)
