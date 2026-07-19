from __future__ import annotations

import numpy as np

from namma_dashcam.alignment import select_event_frames
from namma_dashcam.frame_buffer import FrameRecord


def _frame(ts: float) -> FrameRecord:
    return FrameRecord(monotonic_ts=ts, wall_ts=f"{ts}", frame=np.zeros((4, 4, 3), dtype=np.uint8))


def test_select_event_frames_uses_offset_window() -> None:
    frames = [_frame(10.0), _frame(10.8), _frame(11.0), _frame(11.2), _frame(12.0)]

    selected = select_event_frames(
        event_ts_ms=5_000,
        offset_ms=6_000,
        frames=frames,
        window_pre_ms=250,
        window_post_ms=250,
    )

    assert [frame.monotonic_ts for frame in selected] == [10.8, 11.0, 11.2]
