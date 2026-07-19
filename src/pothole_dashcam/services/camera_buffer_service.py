"""Fixed-window camera frame buffer backed by SQLite metadata."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from pothole_dashcam.models import FrameRef


class CameraBufferService:
    """Persist and retrieve camera frames by timestamp with bounded retention."""

    def __init__(
        self,
        db_path: str | Path,
        image_dir: str | Path,
        retention_minutes: int,
        max_frames: int | None = None,
    ) -> None:
        """Initialize persistent frame buffer storage and retention policy.

        The service stores image bytes on disk and keeps a SQLite index for
        deterministic timestamp lookups and bounded pruning.
        """
        if retention_minutes <= 0:
            msg = "retention_minutes must be > 0"
            raise ValueError(msg)

        # Normalize paths once so all internal operations use absolute semantics.
        self._db_path = Path(db_path)
        self._image_dir = Path(image_dir)
        self._retention_minutes = retention_minutes
        self._retention_ms = retention_minutes * 60 * 1000

        # Default hard cap assumes 1 frame per second for the retention duration.
        self._max_frames = max_frames if max_frames is not None else retention_minutes * 60

        # Ensure storage locations exist before opening DB or writing images.
        self._image_dir.mkdir(parents=True, exist_ok=True)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # Single connection is kept for service lifetime.
        self._conn = sqlite3.connect(self._db_path)
        self._init_schema()

    def close(self) -> None:
        """Release SQLite resources.

        Must be called during shutdown to flush transactions and avoid leaking
        file descriptors in long-running processes.
        """
        self._conn.close()

    def capture_once(self, frame_bytes: bytes, now_ms: int | None = None) -> FrameRef:
        """Store one frame and immediately enforce bounded retention.

        The image payload is written to disk first, then indexed in SQLite so
        retrieval by timestamp is O(log n) via SQL index semantics.
        """
        # Use supplied timestamp for tests/deterministic replay; otherwise wall clock.
        capture_ts_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        frame_id = str(capture_ts_ms)
        file_path = self._image_dir / f"frame_{capture_ts_ms}.jpg"

        # Persist raw frame bytes as file artifact.
        file_path.write_bytes(frame_bytes)

        # Insert (or overwrite) metadata entry for timestamp lookup.
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO frames(timestamp_ms, file_path, created_at_ms)
                VALUES (?, ?, ?)
                """,
                (capture_ts_ms, str(file_path), capture_ts_ms),
            )

        # Keep buffer bounded on every write so growth is deterministic.
        self.prune_old_frames(now_ms=capture_ts_ms)
        return FrameRef(frame_id=frame_id, path=str(file_path), timestamp_ms=capture_ts_ms)

    def get_frame_for_timestamp(self, ts_ms: int, tolerance_ms: int = 1000) -> FrameRef | None:
        """Return nearest frame for a target timestamp within allowed tolerance.

        If no frame exists within `tolerance_ms`, return None instead of a stale
        image so downstream inference does not operate on unrelated data.
        """
        if tolerance_ms < 0:
            msg = "tolerance_ms must be >= 0"
            raise ValueError(msg)

        # Find nearest frame by absolute timestamp distance.
        row = self._conn.execute(
            """
            SELECT timestamp_ms, file_path
            FROM frames
            ORDER BY ABS(timestamp_ms - ?) ASC
            LIMIT 1
            """,
            (ts_ms,),
        ).fetchone()
        if row is None:
            return None

        timestamp_ms = int(row[0])
        file_path = str(row[1])

        # Enforce hard distance guard to avoid returning wrong temporal context.
        if abs(timestamp_ms - ts_ms) > tolerance_ms:
            return None

        return FrameRef(frame_id=str(timestamp_ms), path=file_path, timestamp_ms=timestamp_ms)

    def prune_old_frames(self, now_ms: int | None = None) -> int:
        """Evict frames by age and by hard-count cap.

        Two-stage pruning guarantees deterministic memory/storage bounds even if
        capture cadence temporarily exceeds 1 FPS.
        """
        # Use explicit reference time for deterministic tests and replay runs.
        ref_now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        deleted = 0

        # Stage 1: drop anything outside retention time window.
        deleted += self._delete_older_than(ref_now_ms - self._retention_ms)

        # Stage 2: enforce hard count cap (FIFO by timestamp).
        deleted += self._delete_to_max_frames()
        return deleted

    def frame_count(self) -> int:
        """Return current number of indexed frames in buffer."""
        row = self._conn.execute("SELECT COUNT(*) FROM frames").fetchone()
        return int(row[0]) if row is not None else 0

    def _init_schema(self) -> None:
        """Create SQLite schema used for timestamp-to-file lookup."""
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS frames (
                    timestamp_ms INTEGER PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL
                )
                """
            )

    def _delete_older_than(self, cutoff_ms: int) -> int:
        """Delete all frames strictly older than cutoff timestamp."""
        rows = self._conn.execute(
            """
            SELECT timestamp_ms, file_path
            FROM frames
            WHERE timestamp_ms < ?
            ORDER BY timestamp_ms ASC
            """,
            (cutoff_ms,),
        ).fetchall()

        # Remove file artifacts first; DB rows are source-of-truth after commit.
        for _, file_path in rows:
            Path(file_path).unlink(missing_ok=True)

        with self._conn:
            self._conn.execute("DELETE FROM frames WHERE timestamp_ms < ?", (cutoff_ms,))

        return len(rows)

    def _delete_to_max_frames(self) -> int:
        """Trim oldest frames until total count is within configured cap."""
        if self._max_frames <= 0:
            return 0

        row = self._conn.execute("SELECT COUNT(*) FROM frames").fetchone()
        total = int(row[0]) if row is not None else 0
        excess = total - self._max_frames
        if excess <= 0:
            return 0

        # Select the oldest `excess` rows (FIFO by capture timestamp).
        rows = self._conn.execute(
            """
            SELECT timestamp_ms, file_path
            FROM frames
            ORDER BY timestamp_ms ASC
            LIMIT ?
            """,
            (excess,),
        ).fetchall()

        # Remove corresponding files before deleting index rows.
        for _, file_path in rows:
            Path(file_path).unlink(missing_ok=True)

        with self._conn:
            self._conn.execute(
                """
                DELETE FROM frames
                WHERE timestamp_ms IN (
                    SELECT timestamp_ms
                    FROM frames
                    ORDER BY timestamp_ms ASC
                    LIMIT ?
                )
                """,
                (excess,),
            )

        return len(rows)
