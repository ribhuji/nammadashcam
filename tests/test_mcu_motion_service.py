"""Tests for MCU motion parsing and pothole heuristic filtering."""

from pothole_dashcam.services.mcu_motion_service import (
    MotionSample,
    PotholeHeuristicFilter,
    parse_movement_line,
)


def test_parse_movement_line_valid_input() -> None:
    sample = parse_movement_line("A:0.100,-0.200,0.980|G:1.0,2.0,3.0", now_ms=1234)
    assert sample is not None
    assert sample.timestamp_ms == 1234
    assert sample.ax_g == 0.1
    assert sample.ay_g == -0.2
    assert sample.az_g == 0.98


def test_parse_movement_line_invalid_input() -> None:
    assert parse_movement_line("HB,0,1000") is None
    assert parse_movement_line("A:bad,data|G:1,2,3") is None


def test_heuristic_filter_emits_event_on_impact() -> None:
    filter_handle = PotholeHeuristicFilter(
        impact_threshold_g=0.12,
        jerk_threshold_gps=50.0,
        refractory_ms=0,
    )

    first = MotionSample(1000, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
    second = MotionSample(1010, 0.0, 0.0, 1.3, 0.0, 0.0, 0.0)

    assert filter_handle.process(first) is None
    event = filter_handle.process(second)
    assert event is not None
    assert event.impact_g >= 0.12


def test_heuristic_filter_respects_refractory() -> None:
    filter_handle = PotholeHeuristicFilter(
        impact_threshold_g=0.05,
        jerk_threshold_gps=0.5,
        refractory_ms=500,
    )

    baseline = MotionSample(1000, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
    trigger = MotionSample(1010, 0.0, 0.0, 1.2, 0.0, 0.0, 0.0)
    blocked = MotionSample(1200, 0.0, 0.0, 1.25, 0.0, 0.0, 0.0)
    allowed = MotionSample(1700, 0.0, 0.0, 1.3, 0.0, 0.0, 0.0)

    assert filter_handle.process(baseline) is None
    assert filter_handle.process(trigger) is not None
    assert filter_handle.process(blocked) is None
    assert filter_handle.process(allowed) is not None
