from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import pytest

from problems.job_scheduler import JobScheduler


class Clock:
    def __init__(self, now=10):
        self.now = now
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def scheduler(clock):
    return JobScheduler(clock)


@pytest.fixture
def running_batch(scheduler):
    started = Event()
    release = Event()
    calls = []

    def blocking_callback():
        calls.append("first")
        started.set()
        assert release.wait(5)

    scheduler.schedule("first", 0, blocking_callback)
    scheduler.schedule("second", 1, lambda: calls.append("second"))
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(scheduler.run_due)
        try:
            assert started.wait(5)
            yield scheduler, calls, release, future
        finally:
            release.set()
            future.result(timeout=5)


def test_default_clock_is_monotonic(monkeypatch):
    clock = Clock(42)
    monkeypatch.setattr("problems.job_scheduler.time.monotonic", clock)
    scheduler = JobScheduler()
    calls = []
    scheduler.schedule("job", 42, lambda: calls.append("ran"))
    assert scheduler.clock is clock
    assert scheduler.run_due() == 1
    assert calls == ["ran"]


def test_empty_run(scheduler):
    assert scheduler.run_due() == 0


def test_future_job_waits_for_clock(scheduler, clock):
    calls = []
    scheduler.schedule("job", 11, lambda: calls.append("ran"))
    assert scheduler.run_due() == 0
    clock.now = 11
    assert scheduler.run_due() == 1
    assert calls == ["ran"]


def test_orders_by_deadline_then_insertion(scheduler):
    calls = []
    for job_id, deadline in [("z", 3), ("b", 1), ("a", 1), ("c", 2)]:
        scheduler.schedule(job_id, deadline, lambda name=job_id: calls.append(name))
    assert scheduler.run_due() == 4
    assert calls == ["b", "a", "c", "z"]


def test_callback_attempted_only_once(scheduler):
    calls = []
    scheduler.schedule("job", 0, lambda: calls.append("ran"))
    assert scheduler.run_due() == 1
    assert scheduler.run_due() == 0
    assert calls == ["ran"]


def test_duplicate_pending_id_rejected(scheduler):
    calls = []
    scheduler.schedule("job", 0, lambda: calls.append("original"))
    with pytest.raises(ValueError):
        scheduler.schedule("job", 0, lambda: calls.append("replacement"))
    assert scheduler.run_due() == 1
    assert calls == ["original"]


def test_cancel_pending_job(scheduler):
    calls = []
    scheduler.schedule("job", 0, lambda: calls.append("ran"))
    assert scheduler.cancel("job") is True
    assert scheduler.cancel("job") is False
    assert scheduler.run_due() == 0
    assert calls == []


def test_cancel_unknown_id(scheduler):
    assert scheduler.cancel("missing") is False


def test_reuse_id_after_execution(scheduler):
    calls = []
    for number in range(2):
        scheduler.schedule("job", 0, lambda n=number: calls.append(n))
        assert scheduler.run_due() == 1
    assert calls == [0, 1]


def test_reuse_cancelled_id_has_new_insertion_order(scheduler):
    calls = []
    scheduler.schedule("a", 0, lambda: calls.append("cancelled"))
    scheduler.schedule("b", 0, lambda: calls.append("b"))
    assert scheduler.cancel("a")
    scheduler.schedule("a", 0, lambda: calls.append("new a"))
    assert scheduler.run_due() == 2
    assert calls == ["b", "new a"]


def test_exception_counts_and_does_not_stop_batch(scheduler):
    calls = []

    def failing():
        calls.append("failed")
        raise ValueError("callback failure")

    scheduler.schedule("bad", 0, failing)
    scheduler.schedule("good", 1, lambda: calls.append("good"))
    assert scheduler.run_due() == 2
    assert calls == ["failed", "good"]
    assert scheduler.run_due() == 0
    scheduler.schedule("bad", 0, lambda: None)
    assert scheduler.run_due() == 1


def test_shutdown_is_idempotent_and_rejects_scheduling(scheduler):
    scheduler.shutdown()
    scheduler.shutdown()
    with pytest.raises(RuntimeError):
        scheduler.schedule("job", 0, lambda: None)


def test_shutdown_preserves_pending_jobs(scheduler, clock):
    calls = []
    scheduler.schedule("job", 20, lambda: calls.append("ran"))
    scheduler.shutdown()
    assert scheduler.run_due() == 0
    clock.now = 20
    assert scheduler.run_due() == 1
    assert calls == ["ran"]


def test_cancel_after_shutdown(scheduler):
    scheduler.schedule("job", 0, lambda: None)
    scheduler.shutdown()
    assert scheduler.cancel("job") is True
    assert scheduler.run_due() == 0


def test_callback_can_schedule_but_new_job_waits(scheduler):
    calls = []

    def first():
        calls.append("first")
        scheduler.schedule("new", -1, lambda: calls.append("new"))

    scheduler.schedule("first", 0, first)
    assert scheduler.run_due() == 1
    assert calls == ["first"]
    assert scheduler.run_due() == 1
    assert calls == ["first", "new"]


def test_callback_can_cancel_and_replace_due_job(scheduler):
    calls = []

    def first():
        assert scheduler.cancel("second") is True
        scheduler.schedule("second", 0, lambda: calls.append("replacement"))

    scheduler.schedule("first", 0, first)
    scheduler.schedule("second", 1, lambda: calls.append("cancelled"))
    assert scheduler.run_due() == 1
    assert calls == []
    assert scheduler.run_due() == 1
    assert calls == ["replacement"]


def test_callback_cannot_cancel_or_reuse_own_executing_id(scheduler):
    observed = []

    def callback():
        observed.append(scheduler.cancel("self"))
        with pytest.raises(ValueError):
            scheduler.schedule("self", 0, lambda: None)
        observed.append("duplicate rejected")

    scheduler.schedule("self", 0, callback)
    assert scheduler.run_due() == 1
    assert observed == [False, "duplicate rejected"]


def test_reentrant_run_does_not_repeat_reserved_jobs(scheduler):
    counts = []
    scheduler.schedule("first", 0, lambda: counts.append(scheduler.run_due()))
    scheduler.schedule("second", 1, lambda: counts.append("second"))
    assert scheduler.run_due() == 2
    assert counts == [0, "second"]


def test_callback_can_shutdown(scheduler):
    calls = []
    scheduler.schedule("first", 0, scheduler.shutdown)
    scheduler.schedule("second", 1, lambda: calls.append("ran"))
    assert scheduler.run_due() == 2
    assert calls == ["ran"]
    with pytest.raises(RuntimeError):
        scheduler.schedule("new", 0, lambda: None)


def test_clock_is_sampled_once_per_run(scheduler, clock):
    calls = []
    scheduler.schedule("advance", 0, lambda: setattr(clock, "now", 100))
    scheduler.schedule("future", 11, lambda: calls.append("future"))
    assert scheduler.run_due() == 1
    assert clock.calls == 1
    assert calls == []
    assert scheduler.run_due() == 1
    assert calls == ["future"]


def test_concurrent_run_cannot_take_reserved_jobs(running_batch):
    scheduler, calls, release, future = running_batch
    assert scheduler.run_due() == 0
    release.set()
    assert future.result(timeout=5) == 2
    assert calls == ["first", "second"]


def test_due_job_can_be_cancelled_from_another_thread(running_batch):
    scheduler, calls, release, future = running_batch
    assert scheduler.cancel("second") is True
    release.set()
    assert future.result(timeout=5) == 1
    assert calls == ["first"]


def test_executing_and_reserved_ids_reject_duplicates(running_batch):
    scheduler, _, _, _ = running_batch
    for job_id in ("first", "second"):
        with pytest.raises(ValueError):
            scheduler.schedule(job_id, 0, lambda: None)
    assert scheduler.cancel("first") is False


def test_schedule_during_execution_waits_for_next_run(running_batch):
    scheduler, calls, release, future = running_batch
    scheduler.schedule("new", -1, lambda: calls.append("new"))
    release.set()
    assert future.result(timeout=5) == 2
    assert calls == ["first", "second"]
    assert scheduler.run_due() == 1
    assert calls == ["first", "second", "new"]


def test_concurrent_unique_scheduling(scheduler):
    barrier = Barrier(8)
    calls = []

    def schedule_batch(worker):
        barrier.wait(timeout=5)
        for index in range(25):
            job_id = f"{worker}-{index}"
            scheduler.schedule(job_id, 0, lambda name=job_id: calls.append(name))

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(schedule_batch, worker) for worker in range(8)]
        for future in futures:
            future.result(timeout=5)
    assert scheduler.run_due() == 200
    assert len(calls) == len(set(calls)) == 200


def test_concurrent_duplicate_scheduling_has_one_winner(scheduler):
    barrier = Barrier(8)

    def register():
        barrier.wait(timeout=5)
        try:
            scheduler.schedule("shared", 0, lambda: None)
        except ValueError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(register) for _ in range(8)]
        assert sum(future.result(timeout=5) for future in futures) == 1
    assert scheduler.run_due() == 1


def test_concurrent_runners_attempt_each_job_once(scheduler):
    barrier = Barrier(8)
    calls = []
    for index in range(200):
        scheduler.schedule(str(index), 0, lambda n=index: calls.append(n))

    def run():
        barrier.wait(timeout=5)
        return scheduler.run_due()

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(run) for _ in range(8)]
        assert sum(future.result(timeout=5) for future in futures) == 200
    assert sorted(calls) == list(range(200))


def test_shutdown_during_execution_drains_reserved_jobs(running_batch):
    scheduler, calls, release, future = running_batch
    scheduler.shutdown()
    with pytest.raises(RuntimeError):
        scheduler.schedule("new", 0, lambda: None)
    release.set()
    assert future.result(timeout=5) == 2
    assert calls == ["first", "second"]


def test_base_exception_releases_unstarted_jobs(scheduler):
    calls = []

    def interrupt():
        raise KeyboardInterrupt

    scheduler.schedule("interrupt", 0, interrupt)
    scheduler.schedule("later", 1, lambda: calls.append("later"))
    with pytest.raises(KeyboardInterrupt):
        scheduler.run_due()
    assert scheduler.cancel("interrupt") is False
    assert scheduler.run_due() == 1
    assert calls == ["later"]
