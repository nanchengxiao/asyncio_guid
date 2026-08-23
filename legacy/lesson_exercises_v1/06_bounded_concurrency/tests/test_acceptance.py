import asyncio

import pytest

from course_testing import load_target

m = load_target(__file__)


@pytest.mark.asyncio
async def test_peak_concurrency_is_bounded_but_not_serial():
    active = 0
    peak = 0
    lock = asyncio.Lock()

    async def fetch_one(item):
        nonlocal active, peak
        async with lock:
            active += 1
            peak = max(peak, active)
        await asyncio.sleep(0.02)
        async with lock:
            active -= 1
        return item * 2

    result = await m.fetch_many(range(8), fetch_one, 3)
    assert result == [i * 2 for i in range(8)]
    assert peak == 3
