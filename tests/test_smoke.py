"""Smoke tests for baseline project health."""

from argparse import Namespace

from pothole_dashcam.main import main


def test_main_runs_without_exception(monkeypatch) -> None:
    """Verify entrypoint executes without crashing."""

    def _stub_args() -> Namespace:
        return Namespace(camera_backend="stub", camera_device_index=0)

    monkeypatch.setattr("pothole_dashcam.main.parse_args", _stub_args)
    main()
