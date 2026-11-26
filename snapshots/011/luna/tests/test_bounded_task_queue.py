import threading
import time
from queue import Empty, Full

import pytest

from problems.bounded_task_queue import BoundedTaskQueue, QueueClosed


@pytest.mark.parametrize("size", [0, -1])
def test_max_size_must_be_positive(size):
    with pytest.raises(ValueError):
        BoundedTaskQueue(size)


def test_fifo_and_qsize():
    queue = BoundedTaskQueue(3)
    for item in ["a", "b", "c"]:
        queue.put(item)
    assert queue.qsize() == 3
    assert [queue.get(), queue.get(), queue.get()] == ["a", "b", "c"]
    assert queue.qsize() == 0


def test_capacity_and_nonblocking_operations():
    queue = BoundedTaskQueue(1)
    queue.put(1)
    with pytest.raises(Full):
        queue.put(2, block=False)
    with pytest.raises(Empty):
        BoundedTaskQueue(1).get(block=False)


def test_put_waits_until_space_available():
    queue = BoundedTaskQueue(1)
    queue.put(1)
    finished = threading.Event()
    thread = threading.Thread(target=lambda: (queue.put(2), finished.set()))
    thread.start()
    assert not finished.wait(0.05)
    assert queue.get() == 1
    assert finished.wait(1)
    thread.join()
    assert queue.get() == 2


def test_get_waits_until_item_available():
    queue = BoundedTaskQueue(1)
    result = []
    thread = threading.Thread(target=lambda: result.append(queue.get()))
    thread.start()
    time.sleep(0.05)
    queue.put("ready")
    thread.join(1)
    assert result == ["ready"]


def test_put_timeout_and_zero_timeout():
    queue = BoundedTaskQueue(1)
    queue.put(1)
    with pytest.raises(Full):
        queue.put(2, timeout=0)
    with pytest.raises(Full):
        queue.put(2, timeout=0.02)


def test_get_timeout_and_zero_timeout():
    queue = BoundedTaskQueue(1)
    with pytest.raises(Empty):
        queue.get(timeout=0)
    with pytest.raises(Empty):
        queue.get(timeout=0.02)


@pytest.mark.parametrize("operation", ["put", "get"])
def test_invalid_timeouts(operation):
    queue = BoundedTaskQueue(1)
    with pytest.raises(ValueError):
        getattr(queue, operation)(1, timeout=-1) if operation == "put" else queue.get(timeout=-1)
    with pytest.raises(ValueError):
        if operation == "put":
            queue.put(1, block=False, timeout=0)
        else:
            queue.get(block=False, timeout=0)


def test_close_is_idempotent_and_drains_items():
    queue = BoundedTaskQueue(2)
    queue.put(1)
    queue.close()
    queue.close()
    assert queue.qsize() == 1
    assert queue.get() == 1
    with pytest.raises(QueueClosed):
        queue.get()
    with pytest.raises(QueueClosed):
        queue.put(2)


def test_close_wakes_blocked_consumer():
    queue = BoundedTaskQueue(1)
    outcome = []

    def consume():
        try:
            queue.get()
        except QueueClosed:
            outcome.append("closed")

    thread = threading.Thread(target=consume)
    thread.start()
    time.sleep(0.05)
    queue.close()
    thread.join(1)
    assert outcome == ["closed"]


def test_close_wakes_blocked_producer():
    queue = BoundedTaskQueue(1)
    queue.put(1)
    outcome = []

    def produce():
        try:
            queue.put(2)
        except QueueClosed:
            outcome.append("closed")

    thread = threading.Thread(target=produce)
    thread.start()
    time.sleep(0.05)
    queue.close()
    thread.join(1)
    assert outcome == ["closed"]
