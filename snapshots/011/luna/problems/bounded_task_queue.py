"""A thread-safe bounded FIFO task queue."""

import time
from collections import deque
from queue import Empty, Full
from threading import Condition


class QueueClosed(Exception):
    """Raised when an operation cannot proceed because the queue is closed."""


class BoundedTaskQueue:
    """A bounded FIFO queue with blocking operations and graceful shutdown."""

    def __init__(self, max_size: int):
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._max_size = max_size
        self._items = deque()
        self._condition = Condition()
        self._closed = False

    @staticmethod
    def _validate_wait(block: bool, timeout: float | None) -> None:
        if not block and timeout is not None:
            raise ValueError("cannot specify timeout for a non-blocking operation")
        if block and timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative")

    def put(self, item: object, block: bool = True, timeout: float | None = None) -> None:
        self._validate_wait(block, timeout)
        with self._condition:
            if self._closed:
                raise QueueClosed
            deadline = None if timeout is None else time.monotonic() + timeout
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
        self._validate_wait(block, timeout)
        with self._condition:
            deadline = None if timeout is None else time.monotonic() + timeout
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
