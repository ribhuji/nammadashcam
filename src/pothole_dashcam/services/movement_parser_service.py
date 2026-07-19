"""Parsing helpers for mixed Arduino serial output."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, cast

from pothole_dashcam.models.movement import MovementEvent

DEFAULT_WINDOW_PRE_MS = 500
DEFAULT_WINDOW_POST_MS = 700


def parse_serial_line(raw_line: bytes | str, received_monotonic_ms: int) -> MovementEvent | None:
    """Parse one serial line into a normalized movement event when valid."""

    text = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else raw_line
    stripped = text.strip()
    if not stripped or not stripped.startswith("{"):
        return None

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    try:
        return normalize_payload(cast(Mapping[str, Any], payload), received_monotonic_ms)
    except (KeyError, TypeError, ValueError):
        return None


def normalize_payload(payload: Mapping[str, Any], received_monotonic_ms: int) -> MovementEvent:
    """Validate and normalize a serial JSON payload."""

    return MovementEvent(
        event_id=int(payload["event_id"]),
        arduino_timestamp_ms=int(payload["arduino_timestamp_ms"]),
        received_monotonic_ms=received_monotonic_ms,
        severity=float(payload["severity"]),
        confidence=float(payload["confidence"]),
        window_pre_ms=int(payload.get("window_pre_ms", DEFAULT_WINDOW_PRE_MS)),
        window_post_ms=int(payload.get("window_post_ms", DEFAULT_WINDOW_POST_MS)),
        raw_payload=dict(payload),
    )
