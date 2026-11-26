"""Thread-safe, manually driven in-memory job scheduler."""

import time
from collections.abc import Callable


class JobScheduler:
    """Schedule callbacks for execution through run_due()."""

    def __init__(self, clock=None):
        self.clock = time.monotonic if clock is None else clock

    def schedule(
        self,
        job_id: str,
        run_at: float,
        callback: Callable[[], None],
    ) -> None:
        """Register a job for future execution."""
        raise NotImplementedError

    def cancel(self, job_id: str) -> bool:
        """Cancel a pending job, returning whether it was cancelled."""
        raise NotImplementedError

    def run_due(self) -> int:
        """Attempt jobs due at invocation time."""
        raise NotImplementedError

    def shutdown(self) -> None:
        """Prevent new scheduling while allowing pending jobs to drain."""
        raise NotImplementedError
