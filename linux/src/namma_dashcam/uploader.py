"""Verified incident uploader."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from namma_dashcam.config import Settings
from namma_dashcam.verifier import VerificationResult


@dataclass(slots=True)
class UploadResult:
    success: bool
    status_code: int | None = None
    error: str | None = None


def build_api_payload(
    event: Mapping[str, Any],
    verification: VerificationResult,
    image_path: str | None,
) -> dict[str, Any]:
    """Build the outbound incident payload."""

    return {
        "event_id": int(event["event_id"]),
        "arduino_timestamp_ms": int(event["arduino_timestamp_ms"]),
        "captured_at": datetime.now(tz=UTC).isoformat(),
        "speed_mps": float(event["speed_mps"]),
        "gps": {
            "available": bool(event["gps_available"]),
            "latitude": event.get("gps_latitude"),
            "longitude": event.get("gps_longitude"),
            "speed_mps": event.get("gps_speed_mps"),
        },
        "severity": float(event["severity"]),
        "verification_score": float(verification["score"]),
        "image_path": image_path,
        "features": {
            "vertical_peak_g": event.get("vertical_peak_g"),
            "vertical_valley_g": event.get("vertical_valley_g"),
            "jerk_peak_gps": event.get("jerk_peak_gps"),
            "gyro_peak_dps": event.get("gyro_peak_dps"),
            "event_duration_ms": event.get("event_duration_ms"),
        },
    }


def upload_verified_incident(
    settings: Settings,
    payload: Mapping[str, Any],
    image_path: str | None,
) -> UploadResult:
    """Upload a verified incident to the configured API."""

    headers: dict[str, str] = {}
    if settings.api_token:
        headers["Authorization"] = f"Bearer {settings.api_token}"

    endpoint = f"{settings.api_base_url.rstrip('/')}/incidents"
    try:
        with httpx.Client(timeout=settings.api_timeout_seconds) as client:
            if image_path:
                image_file = Path(image_path)
                with image_file.open("rb") as handle:
                    response = client.post(
                        endpoint,
                        headers=headers,
                        data={"metadata": json.dumps(dict(payload))},
                        files={"image": (image_file.name, handle, "image/jpeg")},
                    )
            else:
                response = client.post(endpoint, headers=headers, json=dict(payload))
    except (OSError, httpx.HTTPError) as exc:
        return UploadResult(success=False, error=str(exc))

    if response.is_success:
        return UploadResult(success=True, status_code=response.status_code)
    return UploadResult(
        success=False,
        status_code=response.status_code,
        error=response.text,
    )
