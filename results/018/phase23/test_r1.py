"""Independent R1 regression, valid for lock-held and lock-free clock reads."""
from threading import Event, Thread

from problems.job_scheduler import JobScheduler


def test_jobs_scheduled_during_clock_read_wait_for_next_invocation():
    entered_clock, release_clock = Event(), Event()
    schedule_started, schedule_finished = Event(), Event()
    calls, attempts, errors = [], [], []

    def clock():
        entered_clock.set()
        if not release_clock.wait(5):
            raise RuntimeError('clock release timed out')
        return 10

    scheduler = JobScheduler(clock=clock)
    scheduler.schedule('original', 1, lambda: calls.append('original'))

    def run():
        try:
            attempts.append(scheduler.run_due())
        except BaseException as exc:
            errors.append(repr(exc))

    def add():
        try:
            schedule_started.set()
            scheduler.schedule('new', 2, lambda: calls.append('new'))
        except BaseException as exc:
            errors.append(repr(exc))
        finally:
            schedule_finished.set()

    runner = Thread(target=run, daemon=True)
    adder = Thread(target=add, daemon=True)
    runner.start()
    try:
        assert entered_clock.wait(5), 'clock was not entered'
        adder.start()
        assert schedule_started.wait(5), 'scheduler thread did not start'
        # A scheduler holding its lock during clock() may block schedule().
        # Permit that valid implementation; never block the controller on it.
        schedule_finished.wait(1)
    finally:
        release_clock.set()
        runner.join(5)
        if adder.ident is not None:
            adder.join(5)
    assert not runner.is_alive() and not adder.is_alive(), 'workers did not finish'
    assert not errors, errors
    first_calls = calls.copy()
    next_attempts = scheduler.run_due()
    assert (attempts, first_calls, next_attempts, calls) == (
        [1], ['original'], 1, ['original', 'new']
    )
