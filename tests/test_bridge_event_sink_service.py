"""Tests for movement bridge-event sink."""

from __future__ import annotations

import json
from pathlib import Path

from pothole_dashcam.models.movement import MovementEvent
from pothole_dashcam.services.bridge_event_sink_service import (
    BridgeEventFileSink,
    to_bridge_payload,
)


def _event(event_id: int = 7) -> MovementEvent:
    return MovementEvent(
        event_id=event_id,
        arduino_timestamp_ms=1_234,
        received_monotonic_ms=9_999,
        severity=0.78,
        confidence=0.66,
        window_pre_ms=500,
        window_post_ms=700,
        raw_payload={
            "event_id": event_id,
            "arduino_timestamp_ms": 1_234,
            "event_type": "suspected_pothole",
            "speed_mps": 8.4,
            "gps_available": True,
            "gps_speed_mps": 8.9,
            "vertical_peak_g": 2.3,
            "custom_metric": 99,
        },
    )


def test_to_bridge_payload_preserves_required_fields() -> None:
    payload = to_bridge_payload(_event())

    assert payload["event_id"] == 7
    assert payload["arduino_timestamp_ms"] == 1_234
    assert payload["event_type"] == "suspected_pothole"
    assert payload["speed_mps"] == 8.4
    assert payload["gps_available"] is True
    assert payload["severity"] == 0.78
    assert payload["confidence"] == 0.66
    assert payload["window_pre_ms"] == 500
    assert payload["window_post_ms"] == 700


def test_to_bridge_payload_preserves_extra_raw_fields() -> None:
    payload = to_bridge_payload(_event())

    assert payload["gps_speed_mps"] == 8.9
    assert payload["vertical_peak_g"] == 2.3
    assert payload["custom_metric"] == 99


def test_bridge_event_file_sink_appends_jsonl_lines(tmp_path: Path) -> None:
    event_path = tmp_path / "bridge-events.jsonl"
    sink = BridgeEventFileSink(event_path)

    sink.append(_event(event_id=1))
    sink.append(_event(event_id=2))

    lines = event_path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["event_id"] for line in lines] == [1, 2]
    assert all(line.startswith("{") and line.endswith("}") for line in lines)
