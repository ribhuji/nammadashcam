"""Continuous capture loop coordinating camera and frame buffer services."""

from __future__ import annotations

import time
from collections.abc import Callable

from pothole_dashcam.services.camera_buffer_service import CameraBufferService
from pothole_dashcam.services.camera_service import StubCameraService, UsbCameraService


class CaptureLoopService:
    """Capture frames at fixed cadence and persist them into frame buffer."""

    def __init__(
        self,
        camera_service: UsbCameraService | StubCameraService,
        frame_buffer: CameraBufferService,
        capture_interval_s: float = 1.0,
        monotonic_fn: Callable[[], float] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        """Initialize fixed-rate capture loop.

        The loop uses monotonic clock scheduling so drift is bounded and frame
        cadence remains deterministic over long runs.
        """
        if capture_interval_s <= 0.0:
            msg = "capture_interval_s must be > 0"
            raise ValueError(msg)

        self._camera_service = camera_service
        self._frame_buffer = frame_buffer
        self._capture_interval_s = capture_interval_s
        self._monotonic_fn = monotonic_fn if monotonic_fn is not None else time.monotonic
        self._sleep_fn = sleep_fn if sleep_fn is not None else time.sleep

    def run(
        self,
        max_captures: int | None = None,
        max_duration_s: float | None = None,
    ) -> int:
        """Run capture loop until bounded stop condition is reached.

        Returns number of frames captured during this run.
        """
        if max_captures is not None and max_captures <= 0:
            msg = "max_captures must be > 0 when provided"
            raise ValueError(msg)

        if max_duration_s is not None and max_duration_s <= 0.0:
            msg = "max_duration_s must be > 0 when provided"
            raise ValueError(msg)

        started = self._monotonic_fn()
        next_capture_at = started
        captured = 0
        started_ms = int(started * 1000.0)

        while True:
            if max_captures is not None and captured >= max_captures:
                break

            # Do not schedule a capture outside configured duration budget.
            if max_duration_s is not None and (next_capture_at - started) >= max_duration_s:
                break

            now = self._monotonic_fn()
            sleep_s = next_capture_at - now
            if sleep_s > 0.0:
                self._sleep_fn(sleep_s)

            frame_bytes = self._camera_service.capture_jpeg_bytes()
            capture_ts_ms = started_ms + int((next_capture_at - started) * 1000.0)
            self._frame_buffer.capture_once(frame_bytes=frame_bytes, now_ms=capture_ts_ms)
            captured += 1
            next_capture_at += self._capture_interval_s

        return captured
