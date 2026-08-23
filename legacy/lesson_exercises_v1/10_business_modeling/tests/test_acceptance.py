import asyncio
from types import SimpleNamespace

import pytest

from course_testing import load_target

m = load_target(__file__)


@pytest.mark.asyncio
async def test_dag_and_optional_failure_semantics():
    first_started = set()
    first_gate = asyncio.Event()
    second_started = set()
    second_gate = asyncio.Event()

    async def fetch_user(user_id):
        first_started.add("user")
        if len(first_started) == 2:
            first_gate.set()
        await asyncio.wait_for(first_gate.wait(), 0.2)
        return {"id": user_id}

    async def fetch_orders(user_id):
        first_started.add("orders")
        if len(first_started) == 2:
            first_gate.set()
        await asyncio.wait_for(first_gate.wait(), 0.2)
        return [{"id": 1}]

    async def fetch_account(user):
        assert first_started == {"user", "orders"}
        second_started.add("account")
        if len(second_started) == 2:
            second_gate.set()
        await asyncio.wait_for(second_gate.wait(), 0.2)
        return {"balance": 10}

    async def fetch_recommendations(orders):
        second_started.add("recommendations")
        if len(second_started) == 2:
            second_gate.set()
        await asyncio.wait_for(second_gate.wait(), 0.2)
        raise RuntimeError("optional downstream unavailable")

    deps = SimpleNamespace(
        fetch_user=fetch_user,
        fetch_orders=fetch_orders,
        fetch_account=fetch_account,
        fetch_recommendations=fetch_recommendations,
    )
    result = await m.build_dashboard(7, deps)
    assert result["account"] == {"balance": 10}
    assert result["recommendations"] is None


@pytest.mark.asyncio
async def test_required_failure_propagates():
    async def ok(value):
        return value

    async def fetch_user(user_id): return {"id": user_id}
    async def fetch_orders(user_id): return []
    async def fetch_account(user): raise LookupError("required")
    async def fetch_recommendations(orders): return []

    deps = SimpleNamespace(fetch_user=fetch_user, fetch_orders=fetch_orders,
                           fetch_account=fetch_account, fetch_recommendations=fetch_recommendations)
    with pytest.raises(ExceptionGroup):
        await m.build_dashboard(1, deps)
