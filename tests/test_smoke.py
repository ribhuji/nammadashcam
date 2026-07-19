"""Smoke tests for baseline project health."""

from argparse import Namespace
from pathlib import Path

from pothole_dashcam.main import main


def _stub_args() -> Namespace:
    return Namespace(
        camera_backend="stub",
        camera_device_index=0,
        inference_backend="stub",
        onnx_model_path=Path("models/best.onnx"),
        inference_threshold=0.5,
        capture_interval_s=1.0,
        capture_max_frames=1,
        capture_max_seconds=0.0,
    )


def _onnx_missing_args() -> Namespace:
    return Namespace(
        camera_backend="stub",
        camera_device_index=0,
        inference_backend="onnx",
        onnx_model_path=Path("models/does_not_exist.onnx"),
        inference_threshold=0.5,
        capture_interval_s=1.0,
        capture_max_frames=1,
        capture_max_seconds=0.0,
    )


def test_main_runs_without_exception(monkeypatch) -> None:
    """Verify entrypoint executes without crashing."""
    monkeypatch.setattr("pothole_dashcam.main.parse_args", _stub_args)
    main()


def test_main_falls_back_to_stub_when_onnx_model_missing(monkeypatch) -> None:
    """ONNX backend should fallback to stub when model file is unavailable."""
    monkeypatch.setattr("pothole_dashcam.main.parse_args", _onnx_missing_args)
    main()
