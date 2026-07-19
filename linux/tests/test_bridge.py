from __future__ import annotations

import json

from namma_dashcam.bridge import BridgeEventReceiver


def test_bridge_receiver_only_returns_new_events(tmp_path) -> None:
    event_path = tmp_path / "events.jsonl"
    receiver = BridgeEventReceiver(event_path)

    first = {
        "event_id": 1,
        "arduino_timestamp_ms": 1000,
        "event_type": "suspected_pothole",
        "speed_mps": 8.2,
        "gps_available": False,
        "severity": 0.8,
        "confidence": 0.7,
        "window_pre_ms": 500,
        "window_post_ms": 700,
    }
    second = dict(first, event_id=2)

    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(first) + "\n")
    assert [event["event_id"] for event in receiver.poll_events()] == [1]
    assert receiver.poll_events() == []

    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(second) + "\n")
    assert [event["event_id"] for event in receiver.poll_events()] == [2]
