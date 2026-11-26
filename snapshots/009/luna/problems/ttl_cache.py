"""Thread-safe in-memory cache with lazy TTL expiration and LRU eviction."""

import time
from collections import OrderedDict
from collections.abc import Callable
from threading import RLock


class TTLCache:
    def __init__(
        self,
        default_ttl: float,
        max_size: int = 1000,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if default_ttl <= 0:
            raise ValueError("default_ttl must be positive")
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._clock = clock or time.monotonic
        self._entries: OrderedDict[str, tuple[object, float]] = OrderedDict()
        self._lock = RLock()

    def _remove_expired(self, now: float) -> None:
        for key in [key for key, (_, expires) in self._entries.items() if now >= expires]:
            del self._entries[key]

    def set(self, key: str, value: object, ttl: float | None = None) -> None:
        lifetime = self._default_ttl if ttl is None else ttl
        if lifetime <= 0:
            raise ValueError("ttl must be positive")
        with self._lock:
            now = self._clock()
            self._remove_expired(now)
            self._entries[key] = (value, now + lifetime)
            self._entries.move_to_end(key)
            if len(self._entries) > self._max_size:
                self._entries.popitem(last=False)

    def get(self, key: str) -> object | None:
        with self._lock:
            now = self._clock()
            entry = self._entries.get(key)
            if entry is None:
                return None
            value, expires = entry
            if now >= expires:
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return value

    def delete(self, key: str) -> bool:
        with self._lock:
            now = self._clock()
            entry = self._entries.get(key)
            if entry is None:
                return False
            del self._entries[key]
            return now < entry[1]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            self._remove_expired(self._clock())
            return len(self._entries)
