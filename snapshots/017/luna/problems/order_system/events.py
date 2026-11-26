"""In-memory event storage."""

from .models import Event


class EventStore:
    def __init__(self) -> None:
        self._events: list[Event] = []

    def publish(self, event: Event) -> None:
        self._events.append(event)

    def events(self) -> list[Event]:
        return self._events.copy()
