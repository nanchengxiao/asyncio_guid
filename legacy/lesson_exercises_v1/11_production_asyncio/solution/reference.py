from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic


class TransientJobError(Exception):
    pass


@dataclass(frozen=True)
class Job:
    job_id: str
    payload: object


@dataclass
class Metrics:
    received: int = 0
    succeeded: int = 0
    failed: int = 0
    retried: int = 0
    duplicates: int = 0


class RateLimiter:
    def __init__(self, rate_per_second: float):
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be > 0")
        self._interval = 1.0 / rate_per_second
        self._next = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = monotonic()
            delay = max(0.0, self._next - now)
            if delay:
                await asyncio.sleep(delay)
                now = monotonic()
            self._next = max(now, self._next) + self._interval


async def process_jobs(jobs, call_api, save_result, *, queue_size=10, workers=3,
                       api_concurrency=2, write_concurrency=1,
                       rate_per_second=1000.0, request_timeout=1.0, retries=1,
                       logger=None):
    logger = logger or (lambda event, **fields: None)
    metrics = Metrics()
    queue = asyncio.Queue(maxsize=queue_size)
    sentinel = object()
    api_gate = asyncio.Semaphore(api_concurrency)
    write_gate = asyncio.Semaphore(write_concurrency)
    limiter = RateLimiter(rate_per_second)
    seen = set()

    async def call_with_policy(job):
        last_error = None
        for attempt in range(retries + 1):
            await limiter.acquire()
            try:
                async with api_gate:
                    async with asyncio.timeout(request_timeout):
                        return await call_api(job)
            except asyncio.CancelledError:
                raise
            except (TransientJobError, TimeoutError) as exc:
                last_error = exc
                if attempt == retries:
                    raise
                metrics.retried += 1
                logger("job_retry", job_id=job.job_id, attempt=attempt + 1)
        raise last_error

    async def worker():
        while True:
            job = await queue.get()
            try:
                if job is sentinel:
                    return
                try:
                    result = await call_with_policy(job)
                    async with write_gate:
                        await save_result(job, result)
                    metrics.succeeded += 1
                    logger("job_succeeded", job_id=job.job_id)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    metrics.failed += 1
                    logger("job_failed", job_id=job.job_id, error=type(exc).__name__)
            finally:
                queue.task_done()

    async def produce():
        for job in jobs:
            metrics.received += 1
            if job.job_id in seen:
                metrics.duplicates += 1
                logger("job_duplicate", job_id=job.job_id)
                continue
            seen.add(job.job_id)
            await queue.put(job)
        for _ in range(workers):
            await queue.put(sentinel)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(produce())
        for _ in range(workers):
            tg.create_task(worker())

    return metrics
