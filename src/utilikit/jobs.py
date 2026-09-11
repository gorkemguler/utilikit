"""Fire-and-poll job store for slow tools (screenshot, pdf).

In-memory, single-process. A job runs in a background task; the client polls
``GET /v1/jobs/{id}``. TTL-pruned. Not durable - that's fine for a toolbox.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .config import get_settings


@dataclass(slots=True)
class Job:
    id: str
    kind: str
    state: str = "pending"  # pending | running | done | error
    created: float = field(default_factory=time.time)
    finished: float | None = None
    result: Any = None
    error: str = ""

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "state": self.state,
            "created": self.created,
            "finished": self.finished,
            "error": self.error,
            "result_ready": self.state == "done",
        }


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._tasks: set[asyncio.Task] = set()
        self._lock = asyncio.Lock()

    async def submit(self, kind: str, coro_factory) -> Job:
        self._prune()
        job = Job(id=uuid.uuid4().hex[:16], kind=kind)
        async with self._lock:
            self._jobs[job.id] = job

        async def _run() -> None:
            job.state = "running"
            try:
                job.result = await coro_factory()
                job.state = "done"
            except Exception as exc:  # recorded on the job, then re-raised nowhere
                job.state = "error"
                job.error = f"{type(exc).__name__}: {exc}"
            finally:
                job.finished = time.time()

        task = asyncio.create_task(_run())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job

    def get(self, job_id: str) -> Job | None:
        self._prune()
        return self._jobs.get(job_id)

    def _prune(self) -> None:
        ttl = get_settings().job_ttl_seconds
        cutoff = time.time() - ttl
        for jid in [j for j, job in self._jobs.items() if job.created < cutoff]:
            self._jobs.pop(jid, None)


_store: JobStore | None = None


def jobs() -> JobStore:
    global _store
    if _store is None:
        _store = JobStore()
    return _store
