"""MCU serial motion ingestion and pothole heuristic filtering."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MotionSample:
    """Single accelerometer/gyro sample decoded from MCU serial stream."""

    timestamp_ms: int
    ax_g: float
    ay_g: float
    az_g: float
    roll_dps: float
    pitch_dps: float
    yaw_dps: float


@dataclass(frozen=True)
class MotionEvent:
    """Heuristic event that indicates a potential pothole impact."""

    timestamp_ms: int
    impact_g: float
    jerk_gps: float
    magnitude_g: float


class MotionLineSource(Protocol):
    """Contract for reading text lines from a motion source."""

    def readline(self) -> str:
        """Return one line from source (possibly empty)."""
        ...


class SerialMotionLineSource:
    """PySerial-backed line source for MCU motion stream."""

    def __init__(self, port: str, baud: int = 115200, timeout_s: float = 1.0) -> None:
        try:
            import serial  # pylint: disable=import-outside-toplevel
        except ImportError as exc:  # pragma: no cover - runtime dependency on target
            msg = "pyserial is required for serial motion ingestion"
            raise RuntimeError(msg) from exc

        self._serial = serial.Serial(port=port, baudrate=baud, timeout=timeout_s)

    def readline(self) -> str:
        """Read one decoded UTF-8 line from serial device."""
        raw = self._serial.readline()
        if not raw:
            return ""
        return raw.decode("utf-8", errors="ignore").strip()

    def close(self) -> None:
        """Release serial device descriptor."""
        self._serial.close()


class PotholeHeuristicFilter:
    """Compute impact/jerk from acceleration and emit possible pothole events."""

    def __init__(
        self,
        impact_threshold_g: float = 0.22,
        jerk_threshold_gps: float = 5.0,
        refractory_ms: int = 300,
    ) -> None:
        if impact_threshold_g <= 0.0:
            msg = "impact_threshold_g must be > 0"
            raise ValueError(msg)
        if jerk_threshold_gps <= 0.0:
            msg = "jerk_threshold_gps must be > 0"
            raise ValueError(msg)
        if refractory_ms < 0:
            msg = "refractory_ms must be >= 0"
            raise ValueError(msg)

        self._impact_threshold_g = impact_threshold_g
        self._jerk_threshold_gps = jerk_threshold_gps
        self._refractory_ms = refractory_ms
        self._last_mag_g: float | None = None
        self._last_ts_ms: int | None = None
        self._last_event_ts_ms = 0

    def process(self, sample: MotionSample) -> MotionEvent | None:
        """Process one sample and return event when heuristic triggers."""
        magnitude_g = (sample.ax_g**2 + sample.ay_g**2 + sample.az_g**2) ** 0.5
        impact_g = abs(magnitude_g - 1.0)

        jerk_gps = 0.0
        if self._last_mag_g is not None and self._last_ts_ms is not None:
            dt_ms = sample.timestamp_ms - self._last_ts_ms
            if dt_ms > 0:
                jerk_gps = abs(magnitude_g - self._last_mag_g) / (dt_ms / 1000.0)

        self._last_mag_g = magnitude_g
        self._last_ts_ms = sample.timestamp_ms

        if (sample.timestamp_ms - self._last_event_ts_ms) < self._refractory_ms:
            return None

        if impact_g >= self._impact_threshold_g or jerk_gps >= self._jerk_threshold_gps:
            self._last_event_ts_ms = sample.timestamp_ms
            return MotionEvent(
                timestamp_ms=sample.timestamp_ms,
                impact_g=impact_g,
                jerk_gps=jerk_gps,
                magnitude_g=magnitude_g,
            )

        return None


def parse_movement_line(line: str, now_ms: int | None = None) -> MotionSample | None:
    """Parse `A:x,y,z|G:r,p,y` lines emitted by current MCU sketch."""
    clean = line.strip()
    if not clean.startswith("A:") or "|G:" not in clean:
        return None

    accel_part, gyro_part = clean.split("|G:", maxsplit=1)
    accel_values = accel_part[2:].split(",")
    gyro_values = gyro_part.split(",")

    if len(accel_values) != 3 or len(gyro_values) != 3:
        return None

    try:
        ax_g = float(accel_values[0])
        ay_g = float(accel_values[1])
        az_g = float(accel_values[2])
        roll_dps = float(gyro_values[0])
        pitch_dps = float(gyro_values[1])
        yaw_dps = float(gyro_values[2])
    except ValueError:
        return None

    ts_ms = int(time.time() * 1000) if now_ms is None else now_ms
    return MotionSample(
        timestamp_ms=ts_ms,
        ax_g=ax_g,
        ay_g=ay_g,
        az_g=az_g,
        roll_dps=roll_dps,
        pitch_dps=pitch_dps,
        yaw_dps=yaw_dps,
    )
