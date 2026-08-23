import asyncio

async def fetch_orders():
    await asyncio.sleep(0.1)
    return ["order-1", "order-2"]

async def fetch_recommendations():
    await asyncio.sleep(0.5)         # 故意比 time budget 慢
    return ["rec-1"]

async def page_data():
    # required：失败则整个业务结果不成立，不做降级
    orders = await fetch_orders()
    # optional：允许缺少这部分内容，但仍要有明确 time budget
    try:
        async with asyncio.timeout(0.2):
            recommendations = await fetch_recommendations()
    except TimeoutError:
        # degradation：主动返回功能较少但仍可用的结果
        recommendations = None
    return {"orders": orders, "recommendations": recommendations}

async def failing_worker(name):
    await asyncio.sleep(0.05)
    raise ValueError(f"{name} 失败")

async def collect_errors():
    errors = []
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(failing_worker("A"))
            tg.create_task(failing_worker("B"))
    except* ValueError as group:
        # except* 在一组异常里按类型匹配，两个失败都被保留
        errors = [str(e) for e in group.exceptions]
    return errors

async def main():
    print(await page_data())
    print(await collect_errors())

asyncio.run(main())
