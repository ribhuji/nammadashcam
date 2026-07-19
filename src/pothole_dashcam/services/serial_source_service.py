"""Serial-source helpers for the movement sidecar."""

from __future__ import annotations

import os
import select
import termios
import time
from collections.abc import Callable, Iterator
from typing import Protocol

_BAUD_RATE_MAP = {
    9600: termios.B9600,
    19200: termios.B19200,
    38400: termios.B38400,
    57600: termios.B57600,
    115200: termios.B115200,
}


class SerialConnection(Protocol):
    """Minimal line-oriented serial connection protocol."""

    def readline(self) -> bytes:
        """Read one newline-delimited payload or timeout payload."""

    def close(self) -> None:
        """Close the underlying serial connection."""


class PosixSerialConnection:
    """Linux serial connection using only the Python standard library."""

    def __init__(self, device: str, baud_rate: int, timeout_seconds: float) -> None:
        if baud_rate not in _BAUD_RATE_MAP:
            msg = f"unsupported baud rate: {baud_rate}"
            raise ValueError(msg)

        self._device = device
        self._timeout_seconds = timeout_seconds
        self._fd = os.open(device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        self._configure(baud_rate)

    def readline(self) -> bytes:
        """Read bytes until newline or timeout."""

        deadline = time.monotonic() + self._timeout_seconds
        chunks: list[bytes] = []

        while True:
            timeout = max(0.0, deadline - time.monotonic())
            if timeout == 0.0:
                return b"".join(chunks)

            readable, _, _ = select.select([self._fd], [], [], timeout)
            if not readable:
                return b"".join(chunks)

            chunk = os.read(self._fd, 1)
            if not chunk:
                return b"".join(chunks)

            chunks.append(chunk)
            if chunk == b"\n":
                return b"".join(chunks)

    def close(self) -> None:
        """Close the underlying file descriptor."""

        os.close(self._fd)

    def _configure(self, baud_rate: int) -> None:
        attrs = termios.tcgetattr(self._fd)
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CLOCAL | termios.CREAD | termios.CS8
        attrs[3] = 0
        attrs[4] = _BAUD_RATE_MAP[baud_rate]
        attrs[5] = _BAUD_RATE_MAP[baud_rate]
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = 0
        termios.tcsetattr(self._fd, termios.TCSANOW, attrs)
        termios.tcflush(self._fd, termios.TCIFLUSH)


class ArduinoSerialSource:
    """Read timestamped serial lines from an Arduino device."""

    def __init__(
        self,
        device: str,
        baud_rate: int,
        timeout_seconds: float,
        *,
        serial_factory: Callable[[], SerialConnection] | None = None,
        monotonic_ms: Callable[[], int] | None = None,
    ) -> None:
        self._device = device
        self._baud_rate = baud_rate
        self._timeout_seconds = timeout_seconds
        self._serial_factory = serial_factory or self._default_serial_factory
        self._monotonic_ms = monotonic_ms or (lambda: int(time.monotonic() * 1000))

    def iter_lines(self) -> Iterator[tuple[int, bytes]]:
        """Yield read-time timestamps paired with raw serial lines."""

        connection = self._serial_factory()
        try:
            while True:
                yield self._monotonic_ms(), connection.readline()
        finally:
            connection.close()

    def _default_serial_factory(self) -> SerialConnection:
        return PosixSerialConnection(
            device=self._device,
            baud_rate=self._baud_rate,
            timeout_seconds=self._timeout_seconds,
        )
