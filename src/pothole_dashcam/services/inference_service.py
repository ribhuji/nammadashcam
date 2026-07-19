"""Inference service contract and placeholder implementation."""

from __future__ import annotations

from typing import Protocol

from pothole_dashcam.models import FrameRef, InferenceResult


class InferenceService(Protocol):
    """Contract for classifying frames for pothole evidence."""

    def confirm_pothole(self, frames: list[FrameRef]) -> InferenceResult:
        """Return inference result based on provided frames."""
        ...


class StubInferenceService:
    """Placeholder inference service for bootstrap stage."""

    def confirm_pothole(self, frames: list[FrameRef]) -> InferenceResult:
        _ = frames
        return InferenceResult(
            is_pothole=False,
            confidence=0.0,
            label="unknown",
            metadata={},
        )
