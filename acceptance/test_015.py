"""Independent acceptance tests for Experiment 015."""

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import pytest

from problems.job_scheduler import JobScheduler


class FakeClock:
    def __init__(self, value=0.0):
        self.value = value

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def make_scheduler():
    clock = FakeClock()
    return JobScheduler(clock=clock), clock


def test_no_jobs():
    scheduler, _ = make_scheduler()
    assert scheduler.run_due() == 0


def test_future_job_not_executed():
    scheduler, _ = make_scheduler()
    calls = []
    scheduler.schedule("a", 10, lambda: calls.append("a"))
    assert scheduler.run_due() == 0
    assert calls == []


def test_job_executes_at_deadline():
    scheduler, clock = make_scheduler()
    calls = []
    scheduler.schedule("a", 10, lambda: calls.append("a"))
    clock.advance(10)
    assert scheduler.run_due() == 1
    assert calls == ["a"]


def test_job_executes_once():
    scheduler, _ = make_scheduler()
    calls = []
    scheduler.schedule("a", 0, lambda: calls.append("a"))
    assert scheduler.run_due() == 1
    assert scheduler.run_due() == 0
    assert calls == ["a"]


def test_deadline_order():
    scheduler, clock = make_scheduler()
    calls = []
    scheduler.schedule("late", 20, lambda: calls.append("late"))
    scheduler.schedule("early", 5, lambda: calls.append("early"))
    scheduler.schedule("middle", 10, lambda: calls.append("middle"))
    clock.advance(20)
    assert scheduler.run_due() == 3
    assert calls == ["early", "middle", "late"]


def test_equal_deadlines_preserve_insertion_order():
    scheduler, _ = make_scheduler()
    calls = []
    for i in range(5):
        scheduler.schedule(str(i), 0, lambda i=i: calls.append(i))
    assert scheduler.run_due() == 5
    assert calls == list(range(5))


def test_duplicate_pending_id_rejected():
    scheduler, _ = make_scheduler()
    scheduler.schedule("a", 10, lambda: None)
    with pytest.raises(ValueError):
        scheduler.schedule("a", 20, lambda: None)


def test_cancel_pending_job():
    scheduler, clock = make_scheduler()
    calls = []
    scheduler.schedule("a", 10, lambda: calls.append("a"))
    assert scheduler.cancel("a") is True
    clock.advance(10)
    assert scheduler.run_due() == 0
    assert calls == []


def test_cancel_unknown_job():
    scheduler, _ = make_scheduler()
    assert scheduler.cancel("missing") is False


def test_cancel_after_execution():
    scheduler, _ = make_scheduler()
    scheduler.schedule("a", 0, lambda: None)
    scheduler.run_due()
    assert scheduler.cancel("a") is False


def test_shutdown_prevents_scheduling():
    scheduler, _ = make_scheduler()
    scheduler.shutdown()
    with pytest.raises(RuntimeError):
        scheduler.schedule("a", 0, lambda: None)


def test_shutdown_preserves_pending_jobs():
    scheduler, clock = make_scheduler()
    calls = []
    scheduler.schedule("a", 10, lambda: calls.append("a"))
    scheduler.shutdown()
    clock.advance(10)
    assert scheduler.run_due() == 1
    assert calls == ["a"]


def test_shutdown_is_idempotent():
    scheduler, _ = make_scheduler()
    scheduler.shutdown()
    scheduler.shutdown()


def test_callback_can_schedule_another_job():
    scheduler, _ = make_scheduler()
    calls = []

    def first():
        calls.append("first")
        scheduler.schedule("second", 0, lambda: calls.append("second"))

    scheduler.schedule("first", 0, first)
    assert scheduler.run_due() == 1
    assert calls == ["first"]
    assert scheduler.run_due() == 1
    assert calls == ["first", "second"]


def test_callback_can_cancel_another_job():
    scheduler, _ = make_scheduler()
    calls = []

    def first():
        calls.append("first")
        assert scheduler.cancel("second") is True

    scheduler.schedule("first", 0, first)
    scheduler.schedule("second", 0, lambda: calls.append("second"))
    assert scheduler.run_due() == 1
    assert calls == ["first"]


def test_callback_exception_does_not_stop_other_jobs():
    scheduler, _ = make_scheduler()
    calls = []

    def failing():
        raise ValueError("callback failure")

    scheduler.schedule("bad", 0, failing)
    scheduler.schedule("good", 0, lambda: calls.append("good"))
    assert scheduler.run_due() == 2
    assert calls == ["good"]


def test_concurrent_scheduling():
    scheduler, _ = make_scheduler()
    calls = []
    lock = Lock()

    def callback():
        with lock:
            calls.append(1)

    def schedule(i):
        scheduler.schedule(str(i), 0, callback)

    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(schedule, range(100)))

    assert scheduler.run_due() == 100
    assert len(calls) == 100


def test_concurrent_run_due_executes_once():
    scheduler, _ = make_scheduler()
    calls = []
    lock = Lock()

    def callback():
        with lock:
            calls.append(1)

    for i in range(100):
        scheduler.schedule(str(i), 0, callback)

    with ThreadPoolExecutor(max_workers=8) as pool:
        counts = list(pool.map(lambda _: scheduler.run_due(), range(8)))

    assert sum(counts) == 100
    assert len(calls) == 100
