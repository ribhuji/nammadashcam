from __future__ import annotations

import numpy as np

from namma_dashcam.config import Settings
from namma_dashcam.frame_buffer import FrameRecord
from namma_dashcam.storage import persist_event_bundle
from namma_dashcam.verifier import VerificationDecision


def test_persist_event_bundle_writes_metadata_and_evidence(tmp_path) -> None:
    settings = Settings(storage_dir=tmp_path)
    frame = np.full((48, 48, 3), 180, dtype=np.uint8)
    decision = VerificationDecision(
        result={
            "verified": True,
            "score": 0.91,
            "rejection_reason": None,
            "evidence_frame_path": None,
        },
        evidence_frame=FrameRecord(monotonic_ts=1.0, wall_ts="now", frame=frame),
        metrics={"brightness": 180.0},
    )

    bundle_dir = persist_event_bundle(
        settings,
        {"event_id": 7, "arduino_timestamp_ms": 1234},
        decision,
    )

    assert (bundle_dir / "event.json").exists()
    assert (bundle_dir / "verification.json").exists()
    assert (bundle_dir / "evidence.jpg").exists()
