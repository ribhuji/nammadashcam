"""Rolling in-memory frame buffer."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

import numpy as np
import numpy.typing as npt

type FrameArray = npt.NDArray[np.uint8]


@dataclass(slots=True)
class FrameRecord:
    """A captured frame and its timestamps."""

    monotonic_ts: float
    wall_ts: str
    frame: FrameArray
    frame_path: str | None = None


class RollingFrameBuffer:
    """Bounded buffer storing recent frames for event verification."""

    def __init__(self, max_seconds: float, max_frames: int) -> None:
        self.max_seconds = max_seconds
        self.max_frames = max_frames
        self._frames: deque[FrameRecord] = deque()
        self._lock = Lock()

    def append(
        self,
        frame: FrameArray,
        monotonic_ts: float,
        wall_ts: str | None = None,
        frame_path: str | None = None,
    ) -> FrameRecord:
        """Append a frame and evict older entries."""

        if wall_ts is None:
            wall_ts = datetime.now(tz=UTC).isoformat()

        record = FrameRecord(
            monotonic_ts=monotonic_ts,
            wall_ts=wall_ts,
            frame=np.ascontiguousarray(frame.copy()),
            frame_path=frame_path,
        )
        with self._lock:
            self._frames.append(record)
            self._evict_locked(monotonic_ts)
        return record

    def snapshot(self) -> list[FrameRecord]:
        """Return a stable list of buffered frames."""

        with self._lock:
            return list(self._frames)

    def latest(self) -> FrameRecord | None:
        """Return the newest frame if available."""

        with self._lock:
            return self._frames[-1] if self._frames else None

    def get_window(self, start_ts: float, end_ts: float) -> list[FrameRecord]:
        """Return frames whose monotonic timestamps fall within the window."""

        with self._lock:
            return [frame for frame in self._frames if start_ts <= frame.monotonic_ts <= end_ts]

    def _evict_locked(self, latest_ts: float) -> None:
        while self._frames and (latest_ts - self._frames[0].monotonic_ts) > self.max_seconds:
            self._frames.popleft()
        while len(self._frames) > self.max_frames:
            self._frames.popleft()
