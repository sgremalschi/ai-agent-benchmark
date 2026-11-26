import pytest

from problems.job_scheduler import JobScheduler


@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit])
def test_interrupted_batch_preserves_unstarted_jobs(exception):
    scheduler = JobScheduler(clock=lambda: 0)
    calls = []

    def interrupt():
        raise exception()

    scheduler.schedule("first", 0, interrupt)
    scheduler.schedule("second", 0, lambda: calls.append("second"))

    with pytest.raises(exception):
        scheduler.run_due()

    assert scheduler.run_due() == 1
    assert calls == ["second"]
