"""A bounded FIFO queue that can be closed and drained."""

import time
from collections import deque
from queue import Empty, Full
from threading import Condition


class QueueClosed(Exception):
    """The queue no longer accepts items or has been closed and drained."""


class BoundedTaskQueue:
    def __init__(self, max_size: int):
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._max_size = max_size
        self._items: deque[object] = deque()
        self._condition = Condition()
        self._closed = False

    @staticmethod
    def _deadline(block: bool, timeout: float | None) -> float | None:
        if not block and timeout is not None:
            raise ValueError("timeout cannot be supplied with block=False")
        if timeout is not None:
            if timeout < 0:
                raise ValueError("timeout must be nonnegative")
            return time.monotonic() + timeout
        return None

    def put(self, item: object, block: bool = True, timeout: float | None = None) -> None:
        with self._condition:
            # Closure takes precedence so every put after close raises QueueClosed.
            if self._closed:
                raise QueueClosed
            deadline = self._deadline(block, timeout)
            while len(self._items) >= self._max_size:
                if self._closed:
                    raise QueueClosed
                if not block:
                    raise Full
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    raise Full
                self._condition.wait(remaining)
            if self._closed:
                raise QueueClosed
            self._items.append(item)
            self._condition.notify_all()

    def get(self, block: bool = True, timeout: float | None = None) -> object:
        with self._condition:
            deadline = self._deadline(block, timeout)
            while not self._items:
                if self._closed:
                    raise QueueClosed
                if not block:
                    raise Empty
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    raise Empty
                self._condition.wait(remaining)
            item = self._items.popleft()
            self._condition.notify_all()
            return item

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()

    def qsize(self) -> int:
        with self._condition:
            return len(self._items)
