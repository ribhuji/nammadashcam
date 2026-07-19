"""Tests for movement serial parsing."""

from __future__ import annotations

from pothole_dashcam.models.movement import MovementEvent
from pothole_dashcam.services.movement_parser_service import normalize_payload, parse_serial_line


def test_parse_serial_line_ignores_debug_text() -> None:
    assert parse_serial_line("calibration complete\n", 1_000) is None


def test_parse_serial_line_ignores_malformed_json() -> None:
    assert parse_serial_line('{"event_id": 1', 1_000) is None


def test_parse_serial_line_returns_none_for_missing_fields() -> None:
    assert parse_serial_line('{"event_id": 1, "severity": 0.8, "confidence": 0.9}', 1_000) is None


def test_parse_serial_line_normalizes_valid_payload() -> None:
    event = parse_serial_line(
        (
            b'{"event_id": 7, "arduino_timestamp_ms": 1234, "severity": 0.78, '
            b'"confidence": 0.66, "window_pre_ms": 450, "window_post_ms": 800}'
        ),
        9_999,
    )

    assert event == MovementEvent(
        event_id=7,
        arduino_timestamp_ms=1_234,
        received_monotonic_ms=9_999,
        severity=0.78,
        confidence=0.66,
        window_pre_ms=450,
        window_post_ms=800,
        raw_payload={
            "event_id": 7,
            "arduino_timestamp_ms": 1234,
            "severity": 0.78,
            "confidence": 0.66,
            "window_pre_ms": 450,
            "window_post_ms": 800,
        },
    )


def test_normalize_payload_uses_default_windows() -> None:
    event = normalize_payload(
        {
            "event_id": 9,
            "arduino_timestamp_ms": 2_500,
            "severity": 0.5,
            "confidence": 0.4,
        },
        4_000,
    )

    assert event.window_pre_ms == 500
    assert event.window_post_ms == 700
