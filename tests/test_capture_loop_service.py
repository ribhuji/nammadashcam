"""Tests for fixed-rate capture loop service."""

from __future__ import annotations

from pathlib import Path

from pothole_dashcam.services.camera_buffer_service import CameraBufferService
from pothole_dashcam.services.camera_service import StubCameraService
from pothole_dashcam.services.capture_loop_service import CaptureLoopService


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, duration_s: float) -> None:
        self.now += duration_s


def test_capture_loop_stores_fixed_number_of_frames(tmp_path: Path) -> None:
    """Capture loop should persist each captured frame to buffer."""
    clock = _Clock()
    camera = StubCameraService(stub_frame_bytes=b"frame")
    buffer = CameraBufferService(
        db_path=tmp_path / "frame_index.db",
        image_dir=tmp_path / "frames",
        retention_minutes=10,
        max_frames=600,
    )

    try:
        loop = CaptureLoopService(
            camera_service=camera,
            frame_buffer=buffer,
            capture_interval_s=1.0,
            monotonic_fn=clock.monotonic,
            sleep_fn=clock.sleep,
        )
        captured = loop.run(max_captures=5)
    finally:
        buffer.close()

    assert captured == 5
    assert len(list((tmp_path / "frames").glob("frame_*.jpg"))) == 5


def test_capture_loop_respects_duration_limit(tmp_path: Path) -> None:
    """Duration-bounded loop should stop without exceeding expected cadence."""
    clock = _Clock()
    camera = StubCameraService(stub_frame_bytes=b"frame")
    buffer = CameraBufferService(
        db_path=tmp_path / "frame_index.db",
        image_dir=tmp_path / "frames",
        retention_minutes=10,
        max_frames=600,
    )

    try:
        loop = CaptureLoopService(
            camera_service=camera,
            frame_buffer=buffer,
            capture_interval_s=1.0,
            monotonic_fn=clock.monotonic,
            sleep_fn=clock.sleep,
        )
        captured = loop.run(max_duration_s=3.2)
    finally:
        buffer.close()

    assert captured == 4


def test_capture_loop_uses_buffer_eviction_policy(tmp_path: Path) -> None:
    """Loop should keep only capped frame count based on buffer policy."""
    clock = _Clock()
    camera = StubCameraService(stub_frame_bytes=b"frame")
    buffer = CameraBufferService(
        db_path=tmp_path / "frame_index.db",
        image_dir=tmp_path / "frames",
        retention_minutes=10,
        max_frames=3,
    )

    try:
        loop = CaptureLoopService(
            camera_service=camera,
            frame_buffer=buffer,
            capture_interval_s=1.0,
            monotonic_fn=clock.monotonic,
            sleep_fn=clock.sleep,
        )
        captured = loop.run(max_captures=6)
        count = buffer.frame_count()
    finally:
        buffer.close()

    assert captured == 6
    assert count == 3
    assert len(list((tmp_path / "frames").glob("frame_*.jpg"))) == 3
