"""Tests for USB camera service behavior without hardware."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType

import pytest


class _FakeCapture:
    def __init__(self, is_opened: bool = True) -> None:
        self._is_opened = is_opened
        self.released = False

    def isOpened(self) -> bool:  # noqa: N802
        return self._is_opened

    def read(self) -> tuple[bool, object | None]:
        return True, object()

    def release(self) -> None:
        self.released = True


class _FakeCv2(ModuleType):
    def __init__(self, opened: bool = True) -> None:
        super().__init__("cv2")
        self._capture = _FakeCapture(is_opened=opened)

    def VideoCapture(self, device_index: int) -> _FakeCapture:  # noqa: N802
        _ = device_index
        return self._capture

    def imencode(self, ext: str, frame: object) -> tuple[bool, bytes]:
        _ = ext
        _ = frame
        return True, b"jpeg-bytes"


def test_usb_camera_service_raises_when_cv2_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Service should fail fast when OpenCV dependency is not installed."""
    monkeypatch.setitem(sys.modules, "cv2", None)
    module = importlib.import_module("pothole_dashcam.services.camera_service")

    with pytest.raises(RuntimeError, match="opencv-python-headless"):
        module.UsbCameraService(device_index=0)


def test_usb_camera_service_capture_and_close(monkeypatch: pytest.MonkeyPatch) -> None:
    """Service should capture JPEG bytes and release camera cleanly."""
    fake_cv2 = _FakeCv2(opened=True)
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    module = importlib.import_module("pothole_dashcam.services.camera_service")

    service = module.UsbCameraService(device_index=0)
    payload = service.capture_jpeg_bytes()
    service.close()

    assert payload == b"jpeg-bytes"
    assert fake_cv2._capture.released


def test_usb_camera_service_raises_when_device_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Service should raise if target camera device cannot be opened."""
    fake_cv2 = _FakeCv2(opened=False)
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    module = importlib.import_module("pothole_dashcam.services.camera_service")

    with pytest.raises(RuntimeError, match="unable to open camera device"):
        module.UsbCameraService(device_index=0)
