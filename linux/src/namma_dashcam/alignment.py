"""Event-to-frame alignment helpers."""

from __future__ import annotations

from collections.abc import Sequence

from namma_dashcam.frame_buffer import FrameRecord


def select_event_frames(
    event_ts_ms: int,
    offset_ms: float,
    frames: Sequence[FrameRecord],
    window_pre_ms: int = 1000,
    window_post_ms: int = 1000,
) -> list[FrameRecord]:
    """Select frames around an Arduino event after offset compensation."""

    if not frames:
        return []

    event_monotonic_ts = (event_ts_ms + offset_ms) / 1000.0
    start_ts = event_monotonic_ts - (window_pre_ms / 1000.0)
    end_ts = event_monotonic_ts + (window_post_ms / 1000.0)
    return [frame for frame in frames if start_ts <= frame.monotonic_ts <= end_ts]
