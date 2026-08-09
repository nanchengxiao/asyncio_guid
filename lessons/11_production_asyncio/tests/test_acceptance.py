import asyncio
from time import monotonic

import pytest

from course_testing import load_target

m = load_target(__file__)


@pytest.mark.asyncio
async def test_pipeline_limits_retries_idempotency_and_drain():
    api_active = 0
    api_peak = 0
    write_active = 0
    write_peak = 0
    attempts = {}
    saved = []
    starts = []
    events = []
    lock = asyncio.Lock()

    async def call_api(job):
        nonlocal api_active, api_peak
        starts.append(monotonic())
        async with lock:
            api_active += 1
            api_peak = max(api_peak, api_active)
        try:
            await asyncio.sleep(0.015)
            attempts[job.job_id] = attempts.get(job.job_id, 0) + 1
            if job.job_id == "b" and attempts[job.job_id] == 1:
                raise m.TransientJobError("retry me")
            return f"ok:{job.payload}"
        finally:
            async with lock:
                api_active -= 1

    async def save_result(job, result):
        nonlocal write_active, write_peak
        write_active += 1
        write_peak = max(write_peak, write_active)
        await asyncio.sleep(0.005)
        saved.append((job.job_id, result))
        write_active -= 1

    jobs = [m.Job("a", 1), m.Job("b", 2), m.Job("a", 999), m.Job("c", 3)]
    metrics = await m.process_jobs(
        jobs,
        call_api,
        save_result,
        queue_size=1,
        workers=3,
        api_concurrency=2,
        write_concurrency=1,
        rate_per_second=50.0,
        request_timeout=0.2,
        retries=1,
        logger=lambda event, **fields: events.append((event, fields)),
    )

    assert sorted(saved) == [("a", "ok:1"), ("b", "ok:2"), ("c", "ok:3")]
    assert api_peak <= 2
    assert write_peak == 1
    assert metrics.received == 4
    assert metrics.succeeded == 3
    assert metrics.failed == 0
    assert metrics.retried == 1
    assert metrics.duplicates == 1
    assert any(event == "job_retry" for event, _ in events)
    assert any(event == "job_duplicate" for event, _ in events)
    # Four API attempts are made (b retries); starts are rate-spaced globally.
    assert len(starts) == 4
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    assert min(gaps) >= 0.012
