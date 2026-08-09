import asyncio
import threading
import time

import pytest

from course_testing import load_target

m = load_target(__file__)


@pytest.mark.asyncio
async def test_blocking_loader_moves_off_loop_and_is_bounded():
    active = 0
    peak = 0
    guard = threading.Lock()
    ticks = 0
    done = asyncio.Event()

    def blocking_loader(item_id):
        nonlocal active, peak
        with guard:
            active += 1
            peak = max(peak, active)
        time.sleep(0.04)
        with guard:
            active -= 1
        return item_id * 10

    async def heartbeat():
        nonlocal ticks
        while not done.is_set():
            ticks += 1
            await asyncio.sleep(0.005)

    hb = asyncio.create_task(heartbeat())
    try:
        result = await m.load_profiles(range(6), blocking_loader, limit=2)
    finally:
        done.set()
        await hb

    assert result == [i * 10 for i in range(6)]
    assert peak == 2
    assert ticks >= 5
