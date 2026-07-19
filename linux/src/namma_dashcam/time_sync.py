"""Arduino-to-Linux time offset estimation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from statistics import median


@dataclass(slots=True)
class TimeSyncSample:
    """One observed mapping between Arduino and Linux monotonic clocks."""

    arduino_ms: int
    linux_monotonic_ms: int


class TimeSyncEstimator:
    """Robust rolling offset estimator using the median sample offset."""

    def __init__(self, max_samples: int = 32, default_offset_ms: float = 0.0) -> None:
        self._samples: deque[TimeSyncSample] = deque(maxlen=max_samples)
        self._default_offset_ms = default_offset_ms

    def add_sample(self, arduino_ms: int, linux_monotonic_ms: int) -> None:
        self._samples.append(
            TimeSyncSample(
                arduino_ms=arduino_ms,
                linux_monotonic_ms=linux_monotonic_ms,
            )
        )

    @property
    def offset_ms(self) -> float:
        if not self._samples:
            return self._default_offset_ms
        offsets = [sample.linux_monotonic_ms - sample.arduino_ms for sample in self._samples]
        return float(median(offsets))

    def event_to_monotonic_seconds(self, arduino_ms: int) -> float:
        return (arduino_ms + self.offset_ms) / 1000.0
