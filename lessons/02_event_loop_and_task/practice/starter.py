import asyncio

async def build_dashboard(user_id, fetch_user, fetch_orders):
    # TODO：user 与 orders 是彼此独立的 I/O，应让它们重叠执行。
    user_task = asyncio.create_task(fetch_user(user_id))
    orders_task = asyncio.create_task(fetch_orders(user_id))
    user, orders = await asyncio.gather(user_task, orders_task)
    return {"user": user, "orders": orders}


# 练习代码这里连库都没导入，场景命题依旧是没说清楚返回什么。 总之：场景命题 和 练习代码极度不完善，让学习者无从下手！！
"""
# Practice — dashboard concurrency
user 与 orders 只共享输入 user_id，彼此无数据依赖。实现聚合函数，让两个 I/O 等待尽可能重叠，并确保函数返回前所有自己创建的工作已结束。
验收：`uv run pytest lessons/02_event_loop_and_task/tests -v --learner`
"""


# async def build_dashboard(user_id, fetch_user, fetch_orders):
#     # TODO：user 与 orders 是彼此独立的 I/O，应让它们重叠执行。
#     raise NotImplementedError