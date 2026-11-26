"""In-memory event storage."""

from .models import Event


class EventStore:
    def publish(self, event: Event) -> None:
        raise NotImplementedError

    def events(self) -> list[Event]:
        raise NotImplementedError
