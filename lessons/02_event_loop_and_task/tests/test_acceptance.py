import asyncio

import pytest

from course_testing import load_target

m = load_target(__file__)


@pytest.mark.asyncio
async def test_independent_io_overlaps():
    started = set()
    both_started = asyncio.Event()

    async def fetch_user(user_id):
        started.add("user")
        if len(started) == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), 0.2)
        await asyncio.sleep(0.01)
        return {"id": user_id}

    async def fetch_orders(user_id):
        started.add("orders")
        if len(started) == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), 0.2)
        await asyncio.sleep(0.01)
        return [user_id]

    result = await m.build_dashboard(5, fetch_user, fetch_orders)
    assert result == {"user": {"id": 5}, "orders": [5]}
