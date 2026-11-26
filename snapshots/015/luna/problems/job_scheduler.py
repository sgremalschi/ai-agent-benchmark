"""Thread-safe, manually driven in-memory job scheduler."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock


@dataclass
class _Job:
    job_id: str
    run_at: float
    sequence: int
    callback: Callable[[], None]
    state: str = "pending"


class JobScheduler:
    """Schedule callbacks for execution through run_due()."""

    def __init__(self, clock=None):
        self.clock = time.monotonic if clock is None else clock
        self._lock = Lock()
        self._jobs: dict[str, _Job] = {}
        self._sequence = 0
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
                raise RuntimeError("scheduler has been shut down")
            if job_id in self._jobs:
                raise ValueError(f"job {job_id!r} is already pending or executing")
            job = _Job(job_id, run_at, self._sequence, callback)
            self._sequence += 1
            self._jobs[job_id] = job

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
        now = self.clock()
        with self._lock:
            cutoff = self._sequence
            due = sorted(
                (job for job in self._jobs.values()
                 if job.state == "pending" and job.run_at <= now and job.sequence < cutoff),
                key=lambda job: (job.run_at, job.sequence),
            )
            for job in due:
                job.state = "reserved"

        attempted = 0
        for job in due:
            with self._lock:
                if self._jobs.get(job.job_id) is not job or job.state != "reserved":
                    continue
                job.state = "executing"
            attempted += 1
            try:
                job.callback()
            except Exception:
                pass
            finally:
                with self._lock:
                    if self._jobs.get(job.job_id) is job:
                        del self._jobs[job.job_id]
        return attempted

    def shutdown(self) -> None:
        """Prevent new scheduling while allowing pending jobs to drain."""
        with self._lock:
            self._shutdown = True
