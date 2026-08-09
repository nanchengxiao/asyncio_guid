import asyncio


async def build_dashboard(user_id, deps):
    async with asyncio.TaskGroup() as tg:
        user_task = tg.create_task(deps.fetch_user(user_id))
        orders_task = tg.create_task(deps.fetch_orders(user_id))
    user = user_task.result()
    orders = orders_task.result()

    async def optional_recommendations():
        try:
            return await deps.fetch_recommendations(orders)
        except asyncio.CancelledError:
            raise
        except Exception:
            return None

    async with asyncio.TaskGroup() as tg:
        account_task = tg.create_task(deps.fetch_account(user))
        recommendations_task = tg.create_task(optional_recommendations())

    return {
        "user": user,
        "orders": orders,
        "account": account_task.result(),
        "recommendations": recommendations_task.result(),
    }
