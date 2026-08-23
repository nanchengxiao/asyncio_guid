import asyncio
import inspect

from course_testing import load_target

m = load_target(__file__)


def test_call_creates_coroutine_without_running_body():
    events = []

    async def fetch_order(order_id):
        events.append("order")
        return {"id": order_id, "customer_id": 7}

    async def fetch_customer(customer_id):
        events.append("customer")
        return {"id": customer_id}

    coro = m.build_order_context(3, fetch_order, fetch_customer)
    assert inspect.iscoroutine(coro)
    assert events == []
    result = asyncio.run(coro)
    assert result["customer"]["id"] == 7
    assert events == ["order", "customer"]
