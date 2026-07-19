"""Runtime movement serial sidecar service."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from threading import Event
from typing import Protocol

from pothole_dashcam.models.movement import MovementEvent
from pothole_dashcam.services.bridge_event_sink_service import BridgeEventFileSink
from pothole_dashcam.services.movement_parser_service import parse_serial_line
from pothole_dashcam.services.serial_source_service import ArduinoSerialSource

LOGGER = logging.getLogger(__name__)


class LineSource(Protocol):
    """Source of timestamped serial lines."""

    def iter_lines(self) -> Iterator[tuple[int, bytes | str]]:
        """Yield raw serial lines paired with monotonic receive timestamps."""


class MovementSink(Protocol):
    """Append-only sink for normalized movement events."""

    def append(self, event: MovementEvent) -> None:
        """Persist one movement event."""


class MovementService:
    """Long-running serial-to-bridge adapter."""

    def __init__(
        self,
        serial_source_factory: Callable[[], LineSource],
        bridge_sink: MovementSink,
        reconnect_seconds: float = 5.0,
        *,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._serial_source_factory = serial_source_factory
        self._bridge_sink = bridge_sink
        self._reconnect_seconds = reconnect_seconds
        self._sleep_fn = sleep_fn
        self._stop_event = Event()

    @classmethod
    def from_env(cls) -> MovementService:
        log_level = os.environ.get("NAMMA_DASHCAM_MOVEMENT_LOG_LEVEL", "INFO")
        _configure_logging(log_level)

        serial_port = os.environ.get("NAMMA_DASHCAM_MOVEMENT_SERIAL_PORT", "/dev/ttyACM0")
        baud_rate = int(os.environ.get("NAMMA_DASHCAM_MOVEMENT_SERIAL_BAUD", "115200"))
        timeout_seconds = float(os.environ.get("NAMMA_DASHCAM_MOVEMENT_SERIAL_TIMEOUT", "1.0"))
        reconnect_seconds = float(
            os.environ.get("NAMMA_DASHCAM_MOVEMENT_RECONNECT_SECONDS", "5.0")
        )
        bridge_event_path = Path(
            os.environ.get("NAMMA_DASHCAM_BRIDGE_EVENT_PATH", "runtime/bridge-events.jsonl")
        )

        return cls(
            serial_source_factory=lambda: ArduinoSerialSource(
                device=serial_port,
                baud_rate=baud_rate,
                timeout_seconds=timeout_seconds,
            ),
            bridge_sink=BridgeEventFileSink(bridge_event_path),
            reconnect_seconds=reconnect_seconds,
        )

    def stop(self) -> None:
        """Request shutdown after the current read loop finishes."""

        self._stop_event.set()

    def run_session(self, serial_source: LineSource | None = None) -> None:
        """Run one serial-connection session until stop or source exit."""

        source = serial_source or self._serial_source_factory()
        for received_ms, raw_line in source.iter_lines():
            if self._stop_event.is_set():
                return
            event = parse_serial_line(raw_line, received_ms)
            if event is None:
                continue
            self._bridge_sink.append(event)

    def run_forever(self) -> None:
        """Keep reading serial lines and reconnect on failure."""

        while not self._stop_event.is_set():
            try:
                self.run_session()
            except Exception:
                if self._stop_event.is_set():
                    break
                LOGGER.exception(
                    "movement serial loop failed; reconnecting in %.1f seconds",
                    self._reconnect_seconds,
                )
                self._sleep_fn(self._reconnect_seconds)
                continue

            if self._stop_event.is_set():
                break

            LOGGER.warning(
                "movement serial loop ended; reconnecting in %.1f seconds",
                self._reconnect_seconds,
            )
            self._sleep_fn(self._reconnect_seconds)


def _configure_logging(log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(level)
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
