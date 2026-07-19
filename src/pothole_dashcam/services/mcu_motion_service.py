"""MCU motion ingestion and pothole heuristic filtering."""

from __future__ import annotations

import importlib
import json
import time
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Any, Protocol


@dataclass(frozen=True)
class MotionSample:
    """Single accelerometer/gyro sample decoded from MCU stream."""

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


def _resolve_bridge_api() -> Any:
    """Locate Bridge API across known UNO Q Python module layouts."""
    candidate_imports = (
        ("arduino.app_utils", "Bridge"),
        ("app_utils", "Bridge"),
        ("router_bridge", "Bridge"),
        ("arduino_router_bridge", "Bridge"),
    )

    for module_name, attr_name in candidate_imports:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        if hasattr(module, attr_name):
            return getattr(module, attr_name)

    msg = (
        "UNO Q bridge API not found. Install/enable Router Bridge Python runtime "
        "or set PYTHONPATH to include bridge modules."
    )
    raise RuntimeError(msg)


class BridgeMotionSampleSource:
    """Bridge-backed source that receives MCU motion samples via RPC callbacks."""

    def __init__(self, channel_name: str = "motion_sample", max_queue_size: int = 256) -> None:
        if max_queue_size <= 0:
            msg = "max_queue_size must be > 0"
            raise ValueError(msg)

        self._queue: deque[MotionSample] = deque(maxlen=max_queue_size)
        self._lock = Lock()
        self._bridge_instance: Any | None = None

        bridge_api = _resolve_bridge_api()

        # Support either module-level static API or class instance API.
        if hasattr(bridge_api, "provide"):
            bridge_api.provide(channel_name, self._bridge_callback)
        elif callable(bridge_api):
            self._bridge_instance = bridge_api()
            if not hasattr(self._bridge_instance, "provide"):
                msg = "Bridge API missing provide() registration function"
                raise RuntimeError(msg)
            self._bridge_instance.provide(channel_name, self._bridge_callback)
        else:
            msg = "Bridge API missing provide() registration function"
            raise RuntimeError(msg)

    def _bridge_callback(self, *args, **kwargs) -> None:
        """Decode callback payload and enqueue a normalized motion sample."""
        sample = parse_bridge_callback_payload(args=args, kwargs=kwargs)
        if sample is None:
            return

        with self._lock:
            self._queue.append(sample)

    def read_sample(self) -> MotionSample | None:
        """Return one queued sample received from bridge callback, if available."""
        with self._lock:
            if not self._queue:
                return None
            return self._queue.popleft()

    def close(self) -> None:
        """Release bridge resources when supported by the runtime API."""
        if self._bridge_instance is not None and hasattr(self._bridge_instance, "close"):
            self._bridge_instance.close()


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


def parse_bridge_sample_payload(payload: object, now_ms: int | None = None) -> MotionSample | None:
    """Parse bridge payload variants into normalized MotionSample structure."""
    ts_ms = int(time.time() * 1000) if now_ms is None else now_ms

    # JSON object payload encoded as text.
    if isinstance(payload, str):
        clean = payload.strip()
        if clean.startswith("{"):
            try:
                decoded = json.loads(clean)
            except json.JSONDecodeError:
                return None
            return parse_bridge_sample_payload(decoded, now_ms=ts_ms)

        # Backward compatibility for text serial framing over bridge.
        return parse_movement_line(clean, now_ms=ts_ms)

    if isinstance(payload, dict):
        try:
            sample_ts = int(payload.get("timestamp_ms", ts_ms))
            ax_g = float(payload.get("ax_g", payload["ax"]))
            ay_g = float(payload.get("ay_g", payload["ay"]))
            az_g = float(payload.get("az_g", payload["az"]))
            roll_dps = float(payload.get("roll_dps", payload.get("roll", 0.0)))
            pitch_dps = float(payload.get("pitch_dps", payload.get("pitch", 0.0)))
            yaw_dps = float(payload.get("yaw_dps", payload.get("yaw", 0.0)))
        except (KeyError, TypeError, ValueError):
            return None

        return MotionSample(
            timestamp_ms=sample_ts,
            ax_g=ax_g,
            ay_g=ay_g,
            az_g=az_g,
            roll_dps=roll_dps,
            pitch_dps=pitch_dps,
            yaw_dps=yaw_dps,
        )

    return None


def parse_bridge_callback_payload(args: tuple[Any, ...], kwargs: dict[str, Any]) -> MotionSample | None:
    """Parse callback argument forms used by UNO Q bridge transports."""
    if "payload" in kwargs:
        return parse_bridge_sample_payload(kwargs["payload"])

    if len(args) == 1:
        return parse_bridge_sample_payload(args[0])

    # Expected positional order from MCU: ax, ay, az, roll, pitch, yaw, timestamp_ms.
    if len(args) >= 7:
        try:
            ax_g = float(args[0])
            ay_g = float(args[1])
            az_g = float(args[2])
            roll_dps = float(args[3])
            pitch_dps = float(args[4])
            yaw_dps = float(args[5])
            timestamp_ms = int(float(args[6]))
        except (TypeError, ValueError):
            return None

        return MotionSample(
            timestamp_ms=timestamp_ms,
            ax_g=ax_g,
            ay_g=ay_g,
            az_g=az_g,
            roll_dps=roll_dps,
            pitch_dps=pitch_dps,
            yaw_dps=yaw_dps,
        )

    return None
