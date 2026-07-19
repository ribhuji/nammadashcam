"""Event consumer contract and baseline implementation."""

from __future__ import annotations

from typing import Protocol

from pothole_dashcam.models import Event


class EventConsumer(Protocol):
    """Contract for retrieving the next event from trigger source."""

    def get_next_event(self) -> Event | None:
        """Return next available event, or None if no event exists."""
        ...


class StubEventConsumer:
    """Placeholder implementation until teammate integration is wired."""

    def get_next_event(self) -> Event | None:
        return None
