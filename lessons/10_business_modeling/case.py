import asyncio

async def fetch_user():
    await asyncio.sleep(0.1)
    return {"id": 7}

async def fetch_orders():
    await asyncio.sleep(0.15)
    return [{"id": 101}, {"id": 102}]

async def account_flow(user_task):
    # edge：account 必须先拿到 user 的结果才能开始
    user = await user_task
    await asyncio.sleep(0.1)
    return {"user_id": user["id"], "balance": 100}

async def recommendations_flow(orders_task):
    # edge：recommendations 必须先拿到 orders 的结果才能开始
    orders = await orders_task
    try:
        await asyncio.sleep(0.2)
        raise RuntimeError("推荐服务失败")   # optional 依赖失败
    except RuntimeError:
        return None                          # degradation：允许缺少这部分结果

async def aggregate():
    async with asyncio.TaskGroup() as tg:
        # 第一层：user 与 orders 只共享输入，彼此无依赖，尽早同时开始
        user_task = tg.create_task(fetch_user())
        orders_task = tg.create_task(fetch_orders())
        # 第二层：各自等到前置结果准备好才开始，互不等待对方
        account_task = tg.create_task(account_flow(user_task))
        recommendations_task = tg.create_task(recommendations_flow(orders_task))
    return {
        "user": user_task.result(),                      # required
        "orders": orders_task.result(),                  # required
        "account": account_task.result(),                # required
        "recommendations": recommendations_task.result(),# optional
    }

async def main():
    result = await aggregate()
    if result["recommendations"] is None:
        print("degradation：缺少推荐内容，页面仍返回")
    print(result)

asyncio.run(main())
