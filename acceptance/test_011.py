import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Empty, Full
from threading import Condition, Event, Thread, current_thread

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "candidate"))

from problems.bounded_task_queue import BoundedTaskQueue, QueueClosed


@pytest.fixture
def waiting_queue(monkeypatch):
    """Signal at Condition.wait while its lock is held, before releasing it.

    A controller operation must acquire that same lock, so it cannot overtake
    entry into wait. Instrument the standard primitive, not queue internals.
    A bounded wait also lets failed-notification mutants terminate cleanly.
    """
    waiting = Event()
    original_wait = Condition.wait
    controller = current_thread()

    def observed_wait(condition, timeout=None):
        if current_thread() is not controller:
            waiting.set()
            return original_wait(condition, 2 if timeout is None else timeout)
        return original_wait(condition, timeout)

    monkeypatch.setattr(Condition, "wait", observed_wait)
    return BoundedTaskQueue(1), waiting

def test_invalid_capacity():
    for size in (0, -1):
        with pytest.raises(ValueError):
            BoundedTaskQueue(size)


def test_fifo_and_size():
    q = BoundedTaskQueue(3)
    assert q.qsize() == 0
    q.put("a")
    q.put("b")
    assert q.qsize() == 2
    assert q.get() == "a"
    assert q.get() == "b"
    assert q.qsize() == 0


def test_nonblocking_full_and_empty():
    q = BoundedTaskQueue(1)
    with pytest.raises(Empty):
        q.get(block=False)
    q.put(1)
    with pytest.raises(Full):
        q.put(2, block=False)
    assert q.get(block=False) == 1


def test_invalid_timeout_arguments():
    q = BoundedTaskQueue(1)
    for method, args in (
        (q.put, (1,)),
        (q.get, ()),
    ):
        with pytest.raises(ValueError):
            method(*args, block=False, timeout=0)
        with pytest.raises(ValueError):
            method(*args, block=True, timeout=-1)


def test_get_timeout():
    q = BoundedTaskQueue(1)
    start = time.monotonic()
    with pytest.raises(Empty):
        q.get(timeout=0.05)
    assert time.monotonic() - start >= 0.04


def test_put_timeout():
    q = BoundedTaskQueue(1)
    q.put(1)
    start = time.monotonic()
    with pytest.raises(Full):
        q.put(2, timeout=0.05)
    assert time.monotonic() - start >= 0.04


def test_blocked_get_receives_item(waiting_queue):
    q, started = waiting_queue
    result = []

    def consumer():
        result.append(q.get())

    t = Thread(target=consumer)
    t.start()
    try:
        assert started.wait(1)
        q.put("hello")
        t.join(1)
        assert not t.is_alive()
        assert result == ["hello"]
    finally:
        q.close()
        t.join(1)


def test_blocked_put_proceeds_after_get(waiting_queue):
    q, started = waiting_queue
    q.put("first")
    result = []

    def producer():
        q.put("second")
        result.append("done")

    t = Thread(target=producer)
    t.start()
    try:
        assert started.wait(1)
        assert q.get() == "first"
        t.join(1)
        assert not t.is_alive()
        assert result == ["done"]
        assert q.get() == "second"
    finally:
        q.close()
        t.join(1)


def test_close_is_idempotent_and_rejects_put():
    q = BoundedTaskQueue(2)
    q.close()
    q.close()
    with pytest.raises(QueueClosed):
        q.put(1)
    with pytest.raises(QueueClosed):
        q.put(1, block=False)


def test_close_drains_existing_items():
    q = BoundedTaskQueue(2)
    q.put(1)
    q.put(2)
    q.close()
    assert q.get() == 1
    assert q.get() == 2
    with pytest.raises(QueueClosed):
        q.get()
    with pytest.raises(QueueClosed):
        q.get(block=False)


def test_close_wakes_blocked_consumer(waiting_queue):
    q, started = waiting_queue
    result = []

    def consumer():
        try:
            q.get()
        except QueueClosed:
            result.append("closed")

    t = Thread(target=consumer)
    t.start()
    try:
        assert started.wait(1)
        q.close()
        t.join(1)
        assert not t.is_alive()
        assert result == ["closed"]
    finally:
        q.close()
        t.join(1)


def test_close_wakes_blocked_producer(waiting_queue):
    q, started = waiting_queue
    q.put(1)
    result = []

    def producer():
        try:
            q.put(2)
        except QueueClosed:
            result.append("closed")

    t = Thread(target=producer)
    t.start()
    try:
        assert started.wait(1)
        q.close()
        t.join(1)
        assert not t.is_alive()
        assert result == ["closed"]
        assert q.get() == 1
    finally:
        q.close()
        t.join(1)


def test_concurrent_producers_no_loss():
    q = BoundedTaskQueue(1000)

    def produce(i):
        q.put(i)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(produce, range(500)))

    assert q.qsize() == 500
    assert set(q.get() for _ in range(500)) == set(range(500))


def test_concurrent_consumers_exactly_once():
    q = BoundedTaskQueue(500)
    for i in range(500):
        q.put(i)

    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(lambda _: q.get(), range(500)))

    assert sorted(values) == list(range(500))
    assert q.qsize() == 0


def test_zero_timeout():
    q = BoundedTaskQueue(1)
    with pytest.raises(Empty):
        q.get(timeout=0)
    q.put(1)
    with pytest.raises(Full):
        q.put(2, timeout=0)


def test_closed_queue_reports_remaining_size():
    q = BoundedTaskQueue(3)
    q.put("a")
    q.put("b")
    q.close()
    assert q.qsize() == 2
    assert q.get() == "a"
    assert q.qsize() == 1
