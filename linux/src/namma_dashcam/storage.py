"""Local persistence for verified and rejected event bundles."""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from namma_dashcam.config import Settings
from namma_dashcam.verifier import VerificationDecision

try:
    import cv2 as _cv2
except ModuleNotFoundError:
    _cv2: Any = None

cv2: Any = _cv2


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def persist_event_bundle(
    settings: Settings,
    event: Mapping[str, Any],
    decision: VerificationDecision,
) -> Path:
    """Persist the event, verification output, and evidence frame."""

    event_id = int(event["event_id"])
    bundle_dir = settings.storage_dir / "events" / f"event-{event_id}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    event_payload = dict(event)
    verification_payload: dict[str, Any] = {
        "verified": decision.result["verified"],
        "score": decision.result["score"],
        "rejection_reason": decision.result["rejection_reason"],
        "evidence_frame_path": decision.result["evidence_frame_path"],
        "metrics": decision.metrics,
    }

    evidence_output: Path | None = None
    if decision.evidence_frame is not None:
        evidence_output = bundle_dir / "evidence.jpg"
        if decision.evidence_frame.frame_path:
            source = Path(decision.evidence_frame.frame_path)
            if source.exists():
                shutil.copy2(source, evidence_output)
            elif cv2 is not None:
                cv2.imwrite(str(evidence_output), decision.evidence_frame.frame)
        elif cv2 is not None:
            cv2.imwrite(str(evidence_output), decision.evidence_frame.frame)

    if evidence_output is not None:
        verification_payload["evidence_frame_path"] = str(evidence_output)

    _write_json(bundle_dir / "event.json", event_payload)
    _write_json(bundle_dir / "verification.json", verification_payload)
    return bundle_dir
