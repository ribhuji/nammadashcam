"""Main Linux service entry point."""

from __future__ import annotations

import logging
import time

from namma_dashcam.alignment import select_event_frames
from namma_dashcam.bridge import BridgeEventReceiver, CandidateEvent
from namma_dashcam.camera import CameraCaptureService
from namma_dashcam.config import Settings, get_settings
from namma_dashcam.frame_buffer import RollingFrameBuffer
from namma_dashcam.logging import configure_logging
from namma_dashcam.storage import persist_event_bundle
from namma_dashcam.time_sync import TimeSyncEstimator
from namma_dashcam.upload_queue import UploadQueue
from namma_dashcam.uploader import build_api_payload, upload_verified_incident
from namma_dashcam.verifier import verify_candidate_event

logger = logging.getLogger(__name__)


def _int_value(payload: CandidateEvent, key: str, default: int) -> int:
    value = payload.get(key, default)
    return int(value) if isinstance(value, int | float) else default


def _handle_event(
    settings: Settings,
    event: CandidateEvent,
    frame_buffer: RollingFrameBuffer,
    time_sync: TimeSyncEstimator,
    upload_queue: UploadQueue,
) -> None:
    arrival_ms = int(time.monotonic() * 1000)
    time_sync.add_sample(event["arduino_timestamp_ms"], arrival_ms)

    frames = select_event_frames(
        event_ts_ms=event["arduino_timestamp_ms"],
        offset_ms=time_sync.offset_ms,
        frames=frame_buffer.snapshot(),
        window_pre_ms=_int_value(event, "window_pre_ms", int(settings.clip_pre_seconds * 1000)),
        window_post_ms=_int_value(event, "window_post_ms", int(settings.clip_post_seconds * 1000)),
    )
    decision = verify_candidate_event(event, frames)
    bundle_dir = persist_event_bundle(settings, event, decision)
    evidence_path = (
        str(bundle_dir / "evidence.jpg") if (bundle_dir / "evidence.jpg").exists() else None
    )

    logger.info(
        "event_id=%s verified=%s reason=%s score=%.3f",
        event["event_id"],
        decision.result["verified"],
        decision.result["rejection_reason"],
        decision.result["score"],
    )

    if not decision.result["verified"]:
        return

    payload = build_api_payload(event, decision.result, evidence_path)
    upload_result = upload_verified_incident(settings, payload, evidence_path)
    if upload_result.success:
        logger.info("uploaded event_id=%s status=%s", event["event_id"], upload_result.status_code)
        return

    upload_queue.enqueue(payload, evidence_path)
    logger.warning(
        "queued event_id=%s upload_error=%s",
        event["event_id"],
        upload_result.error,
    )


def run(settings: Settings | None = None) -> None:
    """Run the long-lived verifier service."""

    if settings is None:
        settings = get_settings()

    configure_logging(settings.log_level)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.bridge_event_path.parent.mkdir(parents=True, exist_ok=True)

    frame_buffer = RollingFrameBuffer(
        max_seconds=settings.camera_buffer_seconds,
        max_frames=max(int(settings.camera_buffer_seconds * settings.webcam_fps * 2), 1),
    )
    receiver = BridgeEventReceiver(
        event_path=settings.bridge_event_path,
        poll_interval_seconds=settings.bridge_poll_interval_seconds,
    )
    time_sync = TimeSyncEstimator()
    upload_queue = UploadQueue(settings.storage_dir, settings.upload_retry_seconds)
    camera = CameraCaptureService(settings, frame_buffer)
    camera.start()

    try:
        while True:
            upload_queue.drain(
                lambda payload, image_path: upload_verified_incident(settings, payload, image_path)
            )
            for event in receiver.poll_events():
                _handle_event(settings, event, frame_buffer, time_sync, upload_queue)
            time.sleep(receiver.poll_interval_seconds)
    except KeyboardInterrupt:
        logger.info("shutting down namma-dashcam")
    finally:
        camera.stop()


if __name__ == "__main__":
    run()
