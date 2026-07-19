"""Webcam capture service."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import numpy as np

from namma_dashcam.config import Settings
from namma_dashcam.frame_buffer import RollingFrameBuffer

try:
    import cv2 as _cv2
except ModuleNotFoundError:
    _cv2: Any = None

cv2: Any = _cv2

logger = logging.getLogger(__name__)


class CameraCaptureService:
    """Continuously capture webcam frames into a rolling buffer."""

    def __init__(self, settings: Settings, frame_buffer: RollingFrameBuffer) -> None:
        self.settings = settings
        self.frame_buffer = frame_buffer
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self.capture_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def capture_forever(self) -> None:
        if cv2 is None:
            logger.warning("opencv not installed; camera capture disabled")
            return

        capture = cv2.VideoCapture(self.settings.webcam_device)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.webcam_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.webcam_height)
        capture.set(cv2.CAP_PROP_FPS, self.settings.webcam_fps)

        if not capture.isOpened():
            logger.error("failed to open webcam device %s", self.settings.webcam_device)
            capture.release()
            return

        logger.info("camera capture started on %s", self.settings.webcam_device)
        try:
            while not self._stop_event.is_set():
                ok, frame = capture.read()
                if not ok:
                    time.sleep(0.05)
                    continue
                captured_frame = np.asarray(frame, dtype=np.uint8)
                self.frame_buffer.append(
                    frame=captured_frame,
                    monotonic_ts=time.monotonic(),
                )
        finally:
            capture.release()
            logger.info("camera capture stopped")
