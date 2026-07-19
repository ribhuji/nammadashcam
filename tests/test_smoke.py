"""Smoke tests for baseline project health."""

from pothole_dashcam.main import main


def test_main_runs_without_exception() -> None:
    """Verify entrypoint executes without crashing."""
    main()
