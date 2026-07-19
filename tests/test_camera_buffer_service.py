"""Tests for the fixed-window camera buffer service."""

from __future__ import annotations

from pathlib import Path

from pothole_dashcam.services.camera_buffer_service import CameraBufferService


def test_capture_and_exact_timestamp_lookup(tmp_path: Path) -> None:
    """Captured frame is retrievable by the same timestamp."""
    service = CameraBufferService(
        db_path=tmp_path / "frames.db",
        image_dir=tmp_path / "frames",
        retention_minutes=10,
        max_frames=600,
    )

    try:
        frame = service.capture_once(b"frame-a", now_ms=1_000)
        found = service.get_frame_for_timestamp(ts_ms=1_000, tolerance_ms=0)
    finally:
        service.close()

    assert found is not None
    assert found.timestamp_ms == frame.timestamp_ms
    assert found.path == frame.path
    assert Path(found.path).exists()


def test_nearest_timestamp_lookup_with_tolerance(tmp_path: Path) -> None:
    """Nearest frame is returned when within configured tolerance."""
    service = CameraBufferService(
        db_path=tmp_path / "frames.db",
        image_dir=tmp_path / "frames",
        retention_minutes=10,
        max_frames=600,
    )

    try:
        service.capture_once(b"older", now_ms=2_000)
        service.capture_once(b"near", now_ms=3_200)

        found = service.get_frame_for_timestamp(ts_ms=3_000, tolerance_ms=300)
        missing = service.get_frame_for_timestamp(ts_ms=10_000, tolerance_ms=100)
    finally:
        service.close()

    assert found is not None
    assert found.timestamp_ms == 3_200
    assert missing is None


def test_prune_by_time_window_removes_old_rows_and_files(tmp_path: Path) -> None:
    """Frames older than retention window are evicted on prune."""
    service = CameraBufferService(
        db_path=tmp_path / "frames.db",
        image_dir=tmp_path / "frames",
        retention_minutes=10,
        max_frames=600,
    )

    try:
        old_frame = service.capture_once(b"old", now_ms=0)
        fresh_frame = service.capture_once(b"fresh", now_ms=590_000)

        deleted = service.prune_old_frames(now_ms=601_000)
    finally:
        service.close()

    assert deleted >= 1
    assert not Path(old_frame.path).exists()
    assert Path(fresh_frame.path).exists()


def test_max_frame_cap_eviction_behaves_like_fifo_by_timestamp(tmp_path: Path) -> None:
    """When max frame cap is reached, oldest timestamp is evicted first."""
    service = CameraBufferService(
        db_path=tmp_path / "frames.db",
        image_dir=tmp_path / "frames",
        retention_minutes=10,
        max_frames=3,
    )

    try:
        first = service.capture_once(b"f1", now_ms=1_000)
        service.capture_once(b"f2", now_ms=2_000)
        service.capture_once(b"f3", now_ms=3_000)
        service.capture_once(b"f4", now_ms=4_000)

        first_lookup = service.get_frame_for_timestamp(ts_ms=1_000, tolerance_ms=0)
        latest_lookup = service.get_frame_for_timestamp(ts_ms=4_000, tolerance_ms=0)
        count = service.frame_count()
    finally:
        service.close()

    assert not Path(first.path).exists()
    assert first_lookup is None
    assert latest_lookup is not None
    assert count == 3
