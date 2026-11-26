"""A bounded, thread-safe cache with lazy expiration and LRU eviction."""

from collections import OrderedDict
from collections.abc import Callable
from threading import Lock
from time import monotonic


class TTLCache:
    def __init__(
        self,
        default_ttl: float,
        max_size: int = 1000,
        clock: Callable[[], float] | None = None,
    ):
        if not default_ttl > 0:
            raise ValueError("default_ttl must be positive")
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._clock = monotonic if clock is None else clock
        self._entries: OrderedDict[str, tuple[object, float]] = OrderedDict()
        self._lock = Lock()

    def _remove_expired(self, now: float) -> None:
        """Remove expired entries while the caller holds the lock."""
        expired = [key for key, (_, expiry) in self._entries.items() if now >= expiry]
        for key in expired:
            del self._entries[key]

    def set(self, key: str, value: object, ttl: float | None = None) -> None:
        duration = self._default_ttl if ttl is None else ttl
        if not duration > 0:
            raise ValueError("ttl must be positive")
        with self._lock:
            now = self._clock()
            if key not in self._entries and len(self._entries) >= self._max_size:
                self._remove_expired(now)
                if len(self._entries) >= self._max_size:
                    self._entries.popitem(last=False)
            self._entries[key] = (value, now + duration)
            self._entries.move_to_end(key)

    def get(self, key: str) -> object | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if self._clock() >= expiry:
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return value

    def delete(self, key: str) -> bool:
        with self._lock:
            entry = self._entries.pop(key, None)
            return entry is not None and self._clock() < entry[1]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            self._remove_expired(self._clock())
            return len(self._entries)
