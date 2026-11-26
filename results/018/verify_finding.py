"""Evaluator-only deterministic reproduction of Sol's sole review finding."""
import json
from threading import Event, Thread

import problems.job_scheduler as candidate


def reproduce():
    entered = Event()
    release = Event()
    calls, attempted, errors = [], [], []

    def clock():
        entered.set()
        if not release.wait(5):
            raise RuntimeError('clock release timed out')
        return 10

    scheduler = candidate.JobScheduler(clock=clock)
    scheduler.schedule('original', 1, lambda: calls.append('original'))

    def run():
        try:
            attempted.append(scheduler.run_due())
        except BaseException as exc:
            errors.append(repr(exc))

    worker = Thread(target=run, daemon=True)
    worker.start()
    try:
        assert entered.wait(5), 'run_due did not enter its clock'
        scheduler.schedule('added_during_run', 2, lambda: calls.append('added_during_run'))
    finally:
        release.set()
        worker.join(5)
    assert not worker.is_alive(), 'worker did not finish'
    assert not errors, errors
    first_calls = calls.copy()
    next_attempted = scheduler.run_due()
    return {'first_attempted': attempted[0], 'first_calls': first_calls,
            'next_attempted': next_attempted, 'all_calls': calls,
            'violation_reproduced': attempted == [2] and first_calls == ['original', 'added_during_run'] and next_attempted == 0}


if __name__ == '__main__':
    observations = [reproduce() for _ in range(20)]
    print(json.dumps({'candidate_module': candidate.__file__, 'repetitions': len(observations),
                      'all_reproduced': all(x['violation_reproduced'] for x in observations),
                      'expected': {'first_attempted': 1, 'first_calls': ['original'], 'next_attempted': 1},
                      'observations': observations}, indent=2))
    assert all(x['violation_reproduced'] for x in observations)
