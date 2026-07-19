"""Bridge ingress for MCU candidate events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from pydantic import BaseModel, ConfigDict


class CandidateEvent(TypedDict):
    event_id: int
    arduino_timestamp_ms: int
    event_type: str
    speed_mps: float
    gps_available: bool
    severity: float
    confidence: float
    window_pre_ms: int
    window_post_ms: int
    gps_speed_mps: NotRequired[float]
    gps_latitude: NotRequired[float]
    gps_longitude: NotRequired[float]
    vertical_peak_g: NotRequired[float]
    vertical_valley_g: NotRequired[float]
    jerk_peak_gps: NotRequired[float]
    gyro_peak_dps: NotRequired[float]
    event_duration_ms: NotRequired[float]


class CandidateEventModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: int
    arduino_timestamp_ms: int
    event_type: str = "suspected_pothole"
    speed_mps: float
    gps_available: bool
    severity: float
    confidence: float
    window_pre_ms: int = 500
    window_post_ms: int = 700
    gps_speed_mps: float | None = None
    gps_latitude: float | None = None
    gps_longitude: float | None = None
    vertical_peak_g: float | None = None
    vertical_valley_g: float | None = None
    jerk_peak_gps: float | None = None
    gyro_peak_dps: float | None = None
    event_duration_ms: float | None = None


def parse_candidate_event(raw: str | dict[str, Any]) -> CandidateEvent:
    """Parse and validate a candidate event payload."""

    payload = json.loads(raw) if isinstance(raw, str) else raw
    validated = CandidateEventModel.model_validate(payload)
    compact_payload = {k: v for k, v in validated.model_dump().items() if v is not None}
    return cast(CandidateEvent, compact_payload)


class BridgeEventReceiver:
    """Poll newline-delimited JSON candidate events from a bridge landing file."""

    def __init__(self, event_path: Path, poll_interval_seconds: float = 0.2) -> None:
        self.event_path = event_path
        self.poll_interval_seconds = poll_interval_seconds
        self._offset = 0
        self.event_path.parent.mkdir(parents=True, exist_ok=True)
        self.event_path.touch(exist_ok=True)

    def poll_events(self) -> list[CandidateEvent]:
        """Return newly appended candidate events."""

        file_size = self.event_path.stat().st_size
        if file_size < self._offset:
            self._offset = 0

        events: list[CandidateEvent] = []
        with self.event_path.open("r", encoding="utf-8") as handle:
            handle.seek(self._offset)
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                events.append(parse_candidate_event(stripped))
            self._offset = handle.tell()
        return events
