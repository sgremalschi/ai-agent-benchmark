"""Thread-safe, manually driven in-memory job scheduler."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock


@dataclass
class _Job:
    run_at: float
    callback: Callable[[], None]
    state: str = "pending"


class JobScheduler:
    """Schedule callbacks for execution through run_due()."""

    def __init__(self, clock=None):
        self.clock = time.monotonic if clock is None else clock
        self._lock = Lock()
        self._jobs: dict[str, _Job] = {}
        self._shutdown = False

    def schedule(
        self,
        job_id: str,
        run_at: float,
        callback: Callable[[], None],
    ) -> None:
        """Register a job for future execution."""
        with self._lock:
            if self._shutdown:
                raise RuntimeError("Scheduler has been shut down")
            if job_id in self._jobs:
                raise ValueError(f"Job ID already registered: {job_id}")
            self._jobs[job_id] = _Job(run_at, callback)

    def cancel(self, job_id: str) -> bool:
        """Cancel a pending job, returning whether it was cancelled."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.state == "executing":
                return False
            del self._jobs[job_id]
            return True

    def run_due(self) -> int:
        """Attempt jobs due at invocation time."""
        with self._lock:
            cutoff = self.clock()
            # Dict insertion order and stable sorting resolve equal deadlines.
            due = sorted(
                (
                    (job_id, job)
                    for job_id, job in self._jobs.items()
                    if job.state == "pending" and job.run_at <= cutoff
                ),
                key=lambda item: item[1].run_at,
            )
            for _, job in due:
                job.state = "claimed"

        attempted = 0
        try:
            for job_id, job in due:
                with self._lock:
                    # Cancellation can remove a claimed job and reuse its ID.
                    if self._jobs.get(job_id) is not job:
                        continue
                    job.state = "executing"
                attempted += 1
                try:
                    job.callback()
                except Exception:
                    # A failed callback is still an attempt and is never retried.
                    pass
                finally:
                    with self._lock:
                        del self._jobs[job_id]
        finally:
            # If a BaseException interrupts the batch, release unstarted jobs.
            with self._lock:
                for job_id, job in due:
                    if self._jobs.get(job_id) is job and job.state == "claimed":
                        job.state = "pending"
        return attempted

    def shutdown(self) -> None:
        """Prevent new scheduling while allowing pending jobs to drain."""
        with self._lock:
            self._shutdown = True
