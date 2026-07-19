"""Upload service contract and placeholder implementation."""

from __future__ import annotations

from typing import Protocol

from pothole_dashcam.models import Event, FrameRef, InferenceResult, UploadResult


class UploadService(Protocol):
    """Contract for evidence upload."""

    def upload_evidence(
        self,
        event: Event,
        best_frame: FrameRef | None,
        result: InferenceResult,
    ) -> UploadResult:
        """Upload relevant evidence and return upload outcome."""
        ...


class StubUploadService:
    """Placeholder upload service for local development."""

    def upload_evidence(
        self,
        event: Event,
        best_frame: FrameRef | None,
        result: InferenceResult,
    ) -> UploadResult:
        _ = event
        _ = best_frame
        _ = result
        return UploadResult(uploaded=False, remote_url=None, retryable_error="not_implemented")
