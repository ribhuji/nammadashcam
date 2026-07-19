"""CLI entrypoint for the movement serial sidecar."""

from __future__ import annotations

from pothole_dashcam.services.movement_service import MovementService


def main() -> None:
    """Start the movement sidecar using environment configuration."""

    service = MovementService.from_env()
    service.run_forever()


if __name__ == "__main__":
    main()
