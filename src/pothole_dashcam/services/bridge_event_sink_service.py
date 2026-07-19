"""Append-only bridge-event sink for movement sidecar output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pothole_dashcam.models.movement import MovementEvent


class BridgeEventFileSink:
    """Write bridge-compatible JSONL events to disk."""

    def __init__(self, bridge_event_path: str | Path) -> None:
        self._bridge_event_path = Path(bridge_event_path)
        self._bridge_event_path.parent.mkdir(parents=True, exist_ok=True)
        self._bridge_event_path.touch(exist_ok=True)

    def append(self, event: MovementEvent) -> None:
        """Append one compact JSON object for a normalized movement event."""

        payload = to_bridge_payload(event)
        with self._bridge_event_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")
            handle.flush()


def to_bridge_payload(event: MovementEvent) -> dict[str, Any]:
    """Convert movement event into a bridge-friendly compatibility payload."""

    raw = dict(event.raw_payload)
    payload: dict[str, Any] = dict(raw)
    payload.update(
        {
            "event_id": event.event_id,
            "arduino_timestamp_ms": event.arduino_timestamp_ms,
            "event_type": str(raw.get("event_type", "suspected_pothole")),
            "speed_mps": float(raw.get("speed_mps", raw.get("gps_speed_mps", 0.0))),
            "gps_available": _coerce_bool(raw.get("gps_available", False)),
            "severity": event.severity,
            "confidence": event.confidence,
            "window_pre_ms": event.window_pre_ms,
            "window_post_ms": event.window_post_ms,
        }
    )
    return payload


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off", ""}:
            return False
    return bool(value)
