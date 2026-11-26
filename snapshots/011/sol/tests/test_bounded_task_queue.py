import time
from queue import Empty, Full
from threading import Event, Thread

import pytest

from problems.bounded_task_queue import BoundedTaskQueue, QueueClosed


@pytest.mark.parametrize("size", [0, -1, -10])
def test_invalid_capacity(size):
    with pytest.raises(ValueError):
        BoundedTaskQueue(size)


def test_fifo_and_size():
    queue = BoundedTaskQueue(3)
    items = [object(), None, "last"]
    assert queue.qsize() == 0
    for index, item in enumerate(items, 1):
        queue.put(item)
        assert queue.qsize() == index
    for index, item in enumerate(items):
        assert queue.get() is item
        assert queue.qsize() == 2 - index


def test_nonblocking_full_and_empty():
    queue = BoundedTaskQueue(1)
    with pytest.raises(Empty):
        queue.get(block=False)
    queue.put("first", block=False)
    with pytest.raises(Full):
        queue.put("second", block=False)
    assert queue.qsize() == 1
    assert queue.get(block=False) == "first"


@pytest.mark.parametrize("method", ["put", "get"])
@pytest.mark.parametrize("timeout", [-1, 0, 1])
def test_nonblocking_rejects_any_timeout(method, timeout):
    queue = BoundedTaskQueue(1)
    args = ("item",) if method == "put" else ()
    with pytest.raises(ValueError):
        getattr(queue, method)(*args, block=False, timeout=timeout)


@pytest.mark.parametrize("method", ["put", "get"])
def test_blocking_rejects_negative_timeout(method):
    queue = BoundedTaskQueue(1)
    args = ("item",) if method == "put" else ()
    with pytest.raises(ValueError):
        getattr(queue, method)(*args, timeout=-0.1)


def test_zero_timeout():
    queue = BoundedTaskQueue(1)
    with pytest.raises(Empty):
        queue.get(timeout=0)
    queue.put("item", timeout=0)
    with pytest.raises(Full):
        queue.put("extra", timeout=0)
    assert queue.get(timeout=0) == "item"


@pytest.mark.parametrize("method, exception", [("put", Full), ("get", Empty)])
def test_timeout_waits(method, exception):
    queue = BoundedTaskQueue(1)
    if method == "put":
        queue.put("occupied")
    args = ("extra",) if method == "put" else ()
    start = time.monotonic()
    with pytest.raises(exception):
        getattr(queue, method)(*args, timeout=0.04)
    assert time.monotonic() - start >= 0.04


def observe_waits(queue, monkeypatch, count=1):
    """Signal only once the requested number of actual condition waits occurs."""
    waiting = Event()
    original_wait = queue._condition.wait
    calls = 0

    def wait(timeout=None):
        nonlocal calls
        calls += 1
        if calls >= count:
            waiting.set()
        return original_wait(timeout)

    monkeypatch.setattr(queue._condition, "wait", wait)
    return waiting


def start_worker(action):
    outcomes = []

    def run():
        try:
            outcomes.append(action())
        except Exception as error:
            outcomes.append(error)

    thread = Thread(target=run, daemon=True)
    thread.start()
    return thread, outcomes


def finish(thread):
    thread.join(timeout=3)
    assert not thread.is_alive(), "queue operation failed to wake"


def test_blocked_producer_resumes_when_space_available(monkeypatch):
    queue = BoundedTaskQueue(1)
    queue.put("first")
    waiting = observe_waits(queue, monkeypatch)
    thread, outcomes = start_worker(lambda: queue.put("second"))
    try:
        assert waiting.wait(3)
        assert queue.qsize() == 1
        assert outcomes == []
        assert queue.get() == "first"
        finish(thread)
        assert outcomes == [None]
        assert queue.get() == "second"
    finally:
        queue.close()
        finish(thread)


def test_blocked_consumer_resumes_when_item_available(monkeypatch):
    queue = BoundedTaskQueue(1)
    waiting = observe_waits(queue, monkeypatch)
    thread, outcomes = start_worker(queue.get)
    try:
        assert waiting.wait(3)
        assert outcomes == []
        queue.put("item")
        finish(thread)
        assert outcomes == ["item"]
    finally:
        queue.close()
        finish(thread)


@pytest.mark.parametrize("producer", [True, False])
def test_close_wakes_all_waiters(monkeypatch, producer):
    queue = BoundedTaskQueue(1)
    if producer:
        queue.put("kept")
    waiting = observe_waits(queue, monkeypatch, count=4)
    action = (lambda: queue.put("extra")) if producer else queue.get
    workers = [start_worker(action) for _ in range(4)]
    try:
        assert waiting.wait(3)
    finally:
        queue.close()
        for thread, _ in workers:
            finish(thread)
    for _, outcomes in workers:
        assert len(outcomes) == 1
        assert isinstance(outcomes[0], QueueClosed)
    assert queue.qsize() == int(producer)


def test_close_is_idempotent_and_drains_fifo():
    queue = BoundedTaskQueue(3)
    queue.put(1)
    queue.put(2)
    queue.close()
    queue.close()
    assert queue.qsize() == 2
    assert queue.get() == 1
    assert queue.get(block=False) == 2
    assert queue.qsize() == 0
    for kwargs in ({}, {"block": False}, {"timeout": 0}):
        with pytest.raises(QueueClosed):
            queue.get(**kwargs)


@pytest.mark.parametrize("kwargs", [{}, {"block": False}, {"timeout": 0},
                                   {"timeout": -1}, {"block": False, "timeout": 1}])
def test_all_put_calls_after_close_raise_closed(kwargs):
    queue = BoundedTaskQueue(1)
    queue.close()
    with pytest.raises(QueueClosed):
        queue.put("item", **kwargs)


def test_multiple_producers_and_consumers():
    queue = BoundedTaskQueue(3)

    def produce(producer):
        for index in range(100):
            queue.put((producer, index))

    def consume():
        received = []
        while True:
            try:
                received.append(queue.get())
            except QueueClosed:
                return received

    consumers = [start_worker(consume) for _ in range(3)]
    producers = [start_worker(lambda p=p: produce(p)) for p in range(4)]
    try:
        for thread, outcomes in producers:
            finish(thread)
            assert outcomes == [None]
    finally:
        queue.close()
        for thread, _ in producers + consumers:
            finish(thread)
    received = []
    for _, outcomes in consumers:
        assert len(outcomes) == 1
        assert isinstance(outcomes[0], list)
        received.extend(outcomes[0])
    assert len(received) == 400
    assert set(received) == {(p, i) for p in range(4) for i in range(100)}
    assert queue.qsize() == 0


@pytest.mark.parametrize("method, exception", [("put", Full), ("get", Empty)])
def test_spurious_wakeups_preserve_monotonic_deadline(monkeypatch, method, exception):
    queue = BoundedTaskQueue(1)
    if method == "put":
        queue.put("occupied")
    readings = iter([10.0, 10.0, 10.25, 11.0])
    monkeypatch.setattr(
        "problems.bounded_task_queue.time.monotonic", lambda: next(readings)
    )
    waits = []
    # Returning immediately simulates notification without a state change.
    monkeypatch.setattr(queue._condition, "wait", lambda timeout: waits.append(timeout))
    args = ("extra",) if method == "put" else ()
    with pytest.raises(exception):
        getattr(queue, method)(*args, timeout=1)
    assert waits == [1.0, 0.75]
