"""Persistent retry queue for failed uploads."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

from namma_dashcam.uploader import UploadResult


class PendingUpload(TypedDict):
    payload_path: str
    image_path: str | None
    retry_count: int


class UploadQueue:
    """Store and retry uploads using on-disk JSON files."""

    def __init__(self, storage_dir: Path, retry_seconds: int) -> None:
        self.retry_seconds = retry_seconds
        self.root = storage_dir / "pending_uploads"
        self.root.mkdir(parents=True, exist_ok=True)
        self.payload_root = self.root / "payloads"
        self.payload_root.mkdir(parents=True, exist_ok=True)

    def enqueue(self, payload: Mapping[str, Any], image_path: str | None) -> Path:
        event_id = payload.get("event_id", "unknown")
        token = uuid4().hex[:8]
        payload_path = self.payload_root / f"event-{event_id}-{token}.json"
        entry_path = self.root / f"pending-{event_id}-{token}.json"
        payload_path.write_text(json.dumps(dict(payload), indent=2), encoding="utf-8")
        entry: PendingUpload = {
            "payload_path": str(payload_path),
            "image_path": image_path,
            "retry_count": 0,
        }
        entry_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
        return entry_path

    def drain(
        self,
        uploader: Callable[[dict[str, Any], str | None], UploadResult],
    ) -> list[UploadResult]:
        results: list[UploadResult] = []
        now = time.time()
        for entry_path in sorted(self.root.glob("pending-*.json")):
            if now - entry_path.stat().st_mtime < self.retry_seconds:
                continue

            entry = json.loads(entry_path.read_text(encoding="utf-8"))
            payload_path = Path(entry["payload_path"])
            if not payload_path.exists():
                entry_path.unlink(missing_ok=True)
                continue

            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            result = uploader(payload, entry.get("image_path"))
            results.append(result)
            if result.success:
                payload_path.unlink(missing_ok=True)
                entry_path.unlink(missing_ok=True)
                continue

            entry["retry_count"] = int(entry.get("retry_count", 0)) + 1
            entry_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
        return results
