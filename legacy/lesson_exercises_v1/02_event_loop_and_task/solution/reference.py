import asyncio


async def build_dashboard(user_id, fetch_user, fetch_orders):
    user_task = asyncio.create_task(fetch_user(user_id))
    orders_task = asyncio.create_task(fetch_orders(user_id))
    user, orders = await asyncio.gather(user_task, orders_task)
    return {"user": user, "orders": orders}
