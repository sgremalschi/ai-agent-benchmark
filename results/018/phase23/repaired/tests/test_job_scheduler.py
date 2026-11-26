"""Tests for the manually driven thread-safe job scheduler."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from problems.job_scheduler import JobScheduler


def scheduler_at(value=10):
    return JobScheduler(clock=lambda: value)


def test_jobs_wait_until_due():
    scheduler = scheduler_at()
    calls = []
    scheduler.schedule("later", 11, lambda: calls.append("later"))
    assert scheduler.run_due() == 0
    assert calls == []


def test_due_jobs_run_in_time_order():
    scheduler = scheduler_at()
    calls = []
    scheduler.schedule("late", 9, lambda: calls.append("late"))
    scheduler.schedule("early", 2, lambda: calls.append("early"))
    assert scheduler.run_due() == 2
    assert calls == ["early", "late"]


def test_equal_times_use_insertion_order():
    scheduler = scheduler_at()
    calls = []
    for name in ("a", "b", "c"):
        scheduler.schedule(name, 5, lambda name=name: calls.append(name))
    scheduler.run_due()
    assert calls == ["a", "b", "c"]


def test_cancel_pending_job():
    scheduler = scheduler_at()
    calls = []
    scheduler.schedule("job", 1, lambda: calls.append(True))
    assert scheduler.cancel("job") is True
    assert scheduler.cancel("job") is False
    assert scheduler.run_due() == 0
    assert calls == []


def test_cancel_unknown_id_returns_false():
    assert scheduler_at().cancel("missing") is False


def test_duplicate_pending_id_rejected():
    scheduler = scheduler_at()
    scheduler.schedule("same", 1, lambda: None)
    with pytest.raises(ValueError):
        scheduler.schedule("same", 2, lambda: None)


def test_id_reused_after_cancel():
    scheduler = scheduler_at()
    scheduler.schedule("same", 1, lambda: None)
    scheduler.cancel("same")
    scheduler.schedule("same", 1, lambda: None)
    assert scheduler.run_due() == 1


def test_id_reused_after_execution():
    scheduler = scheduler_at()
    scheduler.schedule("same", 1, lambda: None)
    scheduler.run_due()
    scheduler.schedule("same", 1, lambda: None)
    assert scheduler.run_due() == 1


def test_callback_exception_does_not_stop_later_jobs():
    scheduler = scheduler_at()
    calls = []

    def fail():
        calls.append("fail")
        raise ValueError("expected")

    scheduler.schedule("bad", 1, fail)
    scheduler.schedule("good", 2, lambda: calls.append("good"))
    assert scheduler.run_due() == 2
    assert calls == ["fail", "good"]


def test_callback_attempted_only_once_even_if_it_raises():
    scheduler = scheduler_at()
    calls = []

    def fail():
        calls.append(1)
        raise RuntimeError

    scheduler.schedule("bad", 1, fail)
    assert scheduler.run_due() == 1
    assert scheduler.run_due() == 0
    assert calls == [1]


def test_callback_can_schedule_job_for_next_invocation():
    scheduler = scheduler_at()
    calls = []
    scheduler.schedule("first", 1, lambda: (calls.append("first"), scheduler.schedule(
        "second", 1, lambda: calls.append("second")
    )))
    assert scheduler.run_due() == 1
    assert calls == ["first"]
    assert scheduler.run_due() == 1
    assert calls == ["first", "second"]


def test_callback_can_cancel_another_due_job():
    scheduler = scheduler_at()
    calls = []
    scheduler.schedule("first", 1, lambda: (calls.append("first"), scheduler.cancel("second")))
    scheduler.schedule("second", 2, lambda: calls.append("second"))
    assert scheduler.run_due() == 1
    assert calls == ["first"]


def test_executing_id_cannot_be_cancelled_or_reused():
    scheduler = scheduler_at()
    outcomes = []

    def callback():
        outcomes.append(scheduler.cancel("job"))
        with pytest.raises(ValueError):
            scheduler.schedule("job", 2, lambda: None)

    scheduler.schedule("job", 1, callback)
    scheduler.run_due()
    assert outcomes == [False]


def test_shutdown_is_idempotent_and_pending_jobs_drain():
    scheduler = scheduler_at()
    calls = []
    scheduler.schedule("pending", 1, lambda: calls.append(1))
    scheduler.shutdown()
    scheduler.shutdown()
    with pytest.raises(RuntimeError):
        scheduler.schedule("new", 1, lambda: None)
    assert scheduler.run_due() == 1
    assert calls == [1]


def test_cancel_reserved_due_job_before_its_callback_starts():
    scheduler = scheduler_at()
    calls = []
    started = Event()
    release = Event()
    scheduler.schedule("first", 1, lambda: (started.set(), release.wait()))
    scheduler.schedule("second", 1, lambda: calls.append("second"))
    with ThreadPoolExecutor(max_workers=1) as pool:
        run = pool.submit(scheduler.run_due)
        assert started.wait(2)
        assert scheduler.cancel("second")
        release.set()
        assert run.result(timeout=2) == 1
    assert calls == []


def test_clock_is_injected_and_read_once_per_invocation():
    times = iter([4, 7])
    scheduler = JobScheduler(clock=lambda: next(times))
    calls = []
    scheduler.schedule("job", 5, lambda: calls.append(True))
    assert scheduler.run_due() == 0
    assert scheduler.run_due() == 1
    assert calls == [True]


def test_job_scheduled_during_clock_read_waits_for_next_invocation():
    clock_entered = Event()
    release_clock = Event()

    def clock():
        clock_entered.set()
        assert release_clock.wait(timeout=2)
        return 10

    scheduler = JobScheduler(clock=clock)
    calls = []
    scheduler.schedule("original", 1, lambda: calls.append("original"))
    with ThreadPoolExecutor(max_workers=1) as pool:
        run = pool.submit(scheduler.run_due)
        assert clock_entered.wait(timeout=2)
        scheduler.schedule("concurrent", 2, lambda: calls.append("concurrent"))
        release_clock.set()
        assert run.result(timeout=2) == 1

    assert calls == ["original"]
    # The same blocking clock is safe here because its event remains set.
    assert scheduler.run_due() == 1
    assert calls == ["original", "concurrent"]


def test_concurrent_scheduling_keeps_all_jobs():
    scheduler = scheduler_at(100)
    calls = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda index: scheduler.schedule(
            str(index), index, lambda index=index: calls.append(index)
        ), range(80)))
    assert scheduler.run_due() == 80
    assert len(calls) == 80


def test_concurrent_run_due_calls_do_not_duplicate_execution():
    scheduler = scheduler_at()
    calls = []
    started = Event()
    release = Event()

    def callback():
        calls.append(1)
        started.set()
        release.wait(timeout=2)

    scheduler.schedule("job", 1, callback)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(scheduler.run_due)
        assert started.wait(2)
        second = pool.submit(scheduler.run_due)
        assert second.result(timeout=2) == 0
        release.set()
        assert first.result(timeout=2) == 1
    assert calls == [1]
