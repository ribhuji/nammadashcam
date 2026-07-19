from __future__ import annotations

import numpy as np

from namma_dashcam.bridge import CandidateEvent
from namma_dashcam.frame_buffer import FrameRecord
from namma_dashcam.verifier import verify_candidate_event


def _event() -> CandidateEvent:
    return {
        "event_id": 1,
        "arduino_timestamp_ms": 1000,
        "event_type": "suspected_pothole",
        "speed_mps": 8.0,
        "gps_available": False,
        "severity": 0.9,
        "confidence": 0.8,
        "vertical_peak_g": 2.5,
        "window_pre_ms": 500,
        "window_post_ms": 700,
    }


def test_verifier_accepts_dark_center_depression() -> None:
    frame = np.full((240, 320, 3), 170, dtype=np.uint8)
    frame[140:210, 120:200] = 50
    frame[138:142, 120:200] = 240
    frame[208:212, 120:200] = 240
    decision = verify_candidate_event(
        _event(),
        [FrameRecord(monotonic_ts=1.0, wall_ts="now", frame=frame)],
    )
    assert decision.result["verified"] is True
    assert decision.result["rejection_reason"] is None


def test_verifier_rejects_blurred_scene() -> None:
    frame = np.full((240, 320, 3), 150, dtype=np.uint8)
    decision = verify_candidate_event(
        _event(),
        [FrameRecord(monotonic_ts=1.0, wall_ts="now", frame=frame)],
    )
    assert decision.result["verified"] is False
    assert decision.result["rejection_reason"] == "blurred"


def test_verifier_rejects_speed_breaker_profile() -> None:
    frame = np.full((240, 320, 3), 160, dtype=np.uint8)
    for row in range(130, 210, 12):
        frame[row : row + 6, 60:260] = 240
    decision = verify_candidate_event(
        _event(),
        [FrameRecord(monotonic_ts=1.0, wall_ts="now", frame=frame)],
    )
    assert decision.result["verified"] is False
    assert decision.result["rejection_reason"] == "speed_breaker_profile"
