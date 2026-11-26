"""Thread-safe sliding-window rate limiter."""

import time
from collections import deque
from threading import Lock


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window: float, clock=None):
        if limit <= 0 or window <= 0:
            raise ValueError("limit and window must be positive")

        self.limit = limit
        self.window = window
        self.clock = time.monotonic if clock is None else clock
        self._events = {}
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        """Return whether a request is allowed for this key."""
        with self._lock:
            now = self.clock()
            events = self._events.setdefault(key, deque())

            while events and now - events[0] >= self.window:
                events.popleft()

            if len(events) >= self.limit:
                return False

            events.append(now)
            return True

    def remaining(self, key: str) -> int:
        """Return available request slots for this key."""
        with self._lock:
            now = self.clock()
            events = self._events.get(key, deque())

            while events and now - events[0] >= self.window:
                events.popleft()

            return max(0, self.limit - len(events))

    def reset(self, key: str) -> None:
        """Remove the recorded requests for a key."""
        with self._lock:
            self._events.pop(key, None)
