"""Tests for movement runtime service orchestration."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import suppress

from pothole_dashcam.models.movement import MovementEvent
from pothole_dashcam.services.movement_service import MovementService
from pothole_dashcam.services.serial_source_service import ArduinoSerialSource


class FakeConnection:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = list(lines)
        self.closed = False

    def readline(self) -> bytes:
        if self._lines:
            return self._lines.pop(0)
        raise EOFError("done")

    def close(self) -> None:
        self.closed = True


class RecordingSink:
    def __init__(self, on_append: Callable[[MovementEvent], None] | None = None) -> None:
        self.events: list[MovementEvent] = []
        self.on_append = on_append

    def append(self, event: MovementEvent) -> None:
        self.events.append(event)
        if self.on_append is not None:
            self.on_append(event)


class FailingSource:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def iter_lines(self) -> Iterator[tuple[int, bytes]]:
        raise self._error
        yield


class FiniteSource:
    def __init__(self, items: list[tuple[int, bytes]]) -> None:
        self._items = list(items)

    def iter_lines(self) -> Iterator[tuple[int, bytes]]:
        yield from self._items


def test_arduino_serial_source_timestamps_reads_and_closes_connection() -> None:
    connection = FakeConnection([b"line-one\n", b""])
    source = ArduinoSerialSource(
        device="/dev/null",
        baud_rate=115200,
        timeout_seconds=1.0,
        serial_factory=lambda: connection,
        monotonic_ms=iter([100, 200, 300]).__next__,
    )

    iterator = source.iter_lines()
    assert next(iterator) == (100, b"line-one\n")
    assert next(iterator) == (200, b"")

    with suppress(EOFError):
        next(iterator)

    assert connection.closed is True


def test_movement_service_run_session_appends_only_valid_events() -> None:
    sink = RecordingSink()
    service = MovementService(
        serial_source_factory=lambda: FiniteSource([]),
        bridge_sink=sink,
        reconnect_seconds=0.0,
        sleep_fn=lambda _seconds: None,
    )

    service.run_session(
        FiniteSource(
            [
                (100, b"namma-dashcam: startup\n"),
                (
                    200,
                    (
                        b'{"event_id": 7, "arduino_timestamp_ms": 1234, '
                        b'"severity": 0.78, "confidence": 0.66}'
                    ),
                ),
                (300, b'{"event_id": 8'),
            ]
        )
    )

    assert [event.event_id for event in sink.events] == [7]
    assert sink.events[0].received_monotonic_ms == 200


def test_movement_service_run_forever_reconnects_after_disconnect() -> None:
    sleep_calls: list[float] = []
    sink = RecordingSink()
    sources = iter(
        [
            FailingSource(OSError("serial disconnected")),
            FiniteSource(
                [
                    (
                        400,
                        (
                            b'{"event_id": 9, "arduino_timestamp_ms": 2222, '
                            b'"severity": 0.9, "confidence": 0.7}'
                        ),
                    )
                ]
            ),
        ]
    )

    service = MovementService(
        serial_source_factory=lambda: next(sources),
        bridge_sink=sink,
        reconnect_seconds=0.0,
        sleep_fn=sleep_calls.append,
    )
    sink.on_append = lambda _event: service.stop()

    service.run_forever()

    assert sleep_calls == [0.0]
    assert [event.event_id for event in sink.events] == [9]
