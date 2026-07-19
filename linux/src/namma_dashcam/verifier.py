"""Candidate pothole verification heuristics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

import numpy as np
import numpy.typing as npt

from namma_dashcam.bridge import CandidateEvent
from namma_dashcam.frame_buffer import FrameArray, FrameRecord

try:
    import cv2 as _cv2
except ModuleNotFoundError:
    _cv2: Any = None

cv2: Any = _cv2


class VerificationResult(TypedDict):
    verified: bool
    score: float
    rejection_reason: str | None
    evidence_frame_path: str | None


@dataclass(slots=True)
class VerificationDecision:
    result: VerificationResult
    evidence_frame: FrameRecord | None
    metrics: dict[str, float]


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _to_gray(frame: FrameArray) -> npt.NDArray[np.uint8]:
    if frame.ndim == 2:
        return np.asarray(frame, dtype=np.uint8)
    if cv2 is not None:
        return np.asarray(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), dtype=np.uint8)
    return np.mean(frame, axis=2).astype(np.uint8)


def _road_region(gray: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    height, width = gray.shape
    top = int(height * 0.45)
    bottom = int(height * 0.9)
    left = int(width * 0.2)
    right = int(width * 0.8)
    return gray[top:bottom, left:right]


def _laplacian_variance(gray: npt.NDArray[np.uint8]) -> float:
    if cv2 is not None:
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    gy, gx = np.gradient(gray.astype(np.float32))
    return float((gx**2 + gy**2).var())


def _edge_mask(gray: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    if cv2 is not None:
        return np.asarray(cv2.Canny(gray, 80, 160), dtype=np.uint8)
    gy, gx = np.gradient(gray.astype(np.float32))
    magnitude = np.sqrt(gx**2 + gy**2)
    threshold = float(np.mean(magnitude) + np.std(magnitude))
    return np.asarray((magnitude > threshold).astype(np.uint8) * 255, dtype=np.uint8)


def _frame_metrics(frame: FrameArray) -> dict[str, float]:
    gray = _to_gray(frame)
    road = _road_region(gray)
    road_float = road.astype(np.float32)

    brightness = float(np.mean(road_float))
    blur = _laplacian_variance(road)
    contrast = float(np.std(road_float))

    edges = _edge_mask(road)
    edge_density = float(np.count_nonzero(edges) / edges.size)

    gy, gx = np.gradient(road_float)
    horizontal_energy = float(np.abs(gy).sum())
    vertical_energy = float(np.abs(gx).sum())
    horizontal_ratio = horizontal_energy / (horizontal_energy + vertical_energy + 1e-6)

    height, width = road.shape
    center = road_float[height // 3 : (2 * height) // 3, width // 3 : (2 * width) // 3]
    surround = road_float.copy()
    surround[height // 3 : (2 * height) // 3, width // 3 : (2 * width) // 3] = np.nan
    surround_mean = float(np.nanmean(surround))
    center_drop = max(surround_mean - float(np.mean(center)), 0.0)

    return {
        "brightness": brightness,
        "blur": blur,
        "contrast": contrast,
        "edge_density": edge_density,
        "horizontal_ratio": horizontal_ratio,
        "center_drop": center_drop,
    }


def _select_best_frame(frames: list[FrameRecord]) -> tuple[FrameRecord, dict[str, float]]:
    scored = []
    for frame in frames:
        metrics = _frame_metrics(frame.frame)
        quality = metrics["blur"] + metrics["contrast"]
        scored.append((quality, frame, metrics))
    _, best_frame, best_metrics = max(scored, key=lambda item: item[0])
    return best_frame, best_metrics


def verify_candidate_event(
    event: CandidateEvent,
    frames: list[FrameRecord],
) -> VerificationDecision:
    """Return a verification decision for the candidate event."""

    if not frames:
        return VerificationDecision(
            result={
                "verified": False,
                "score": 0.0,
                "rejection_reason": "no_frames",
                "evidence_frame_path": None,
            },
            evidence_frame=None,
            metrics={},
        )

    evidence_frame, metrics = _select_best_frame(frames)

    if metrics["brightness"] < 40.0:
        return VerificationDecision(
            result={
                "verified": False,
                "score": 0.0,
                "rejection_reason": "low_light",
                "evidence_frame_path": evidence_frame.frame_path,
            },
            evidence_frame=evidence_frame,
            metrics=metrics,
        )

    if metrics["blur"] < 55.0:
        return VerificationDecision(
            result={
                "verified": False,
                "score": 0.0,
                "rejection_reason": "blurred",
                "evidence_frame_path": evidence_frame.frame_path,
            },
            evidence_frame=evidence_frame,
            metrics=metrics,
        )

    if metrics["horizontal_ratio"] > 0.72 and metrics["edge_density"] > 0.08:
        return VerificationDecision(
            result={
                "verified": False,
                "score": 0.0,
                "rejection_reason": "speed_breaker_profile",
                "evidence_frame_path": evidence_frame.frame_path,
            },
            evidence_frame=evidence_frame,
            metrics=metrics,
        )

    motion_score = np.mean(
        [
            _clamp(float(event["severity"])),
            _clamp(float(event["confidence"])),
            _clamp(float(event.get("vertical_peak_g", 0.0)) / 3.0),
        ]
    )
    visual_score = np.mean(
        [
            _clamp(metrics["contrast"] / 70.0),
            _clamp(metrics["center_drop"] / 25.0),
            _clamp(metrics["edge_density"] / 0.20),
        ]
    )
    score = float((0.55 * motion_score) + (0.45 * visual_score))
    verified = score >= 0.55 and metrics["center_drop"] >= 6.0

    return VerificationDecision(
        result={
            "verified": verified,
            "score": score,
            "rejection_reason": None if verified else "visual_score_too_low",
            "evidence_frame_path": evidence_frame.frame_path,
        },
        evidence_frame=evidence_frame,
        metrics=metrics,
    )
