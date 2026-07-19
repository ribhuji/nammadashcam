from __future__ import annotations

from pathlib import Path

from namma_dashcam.upload_queue import UploadQueue
from namma_dashcam.uploader import UploadResult


def test_upload_queue_retries_until_success(tmp_path: Path) -> None:
    queue = UploadQueue(tmp_path, retry_seconds=0)
    queue.enqueue({"event_id": 42, "payload": "value"}, None)

    attempts = {"count": 0}

    def uploader(payload: dict[str, object], image_path: str | None) -> UploadResult:
        assert payload["event_id"] == 42
        assert image_path is None
        attempts["count"] += 1
        if attempts["count"] == 1:
            return UploadResult(success=False, error="offline")
        return UploadResult(success=True, status_code=200)

    first_results = queue.drain(uploader)
    assert len(first_results) == 1
    assert first_results[0].success is False
    assert list((tmp_path / "pending_uploads").glob("pending-*.json"))

    second_results = queue.drain(uploader)
    assert len(second_results) == 1
    assert second_results[0].success is True
    assert list((tmp_path / "pending_uploads").glob("pending-*.json")) == []
