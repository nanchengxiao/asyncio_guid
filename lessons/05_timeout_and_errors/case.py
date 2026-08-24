import asyncio

async def fetch_orders():
    await asyncio.sleep(0.1)
    return ["order-1", "order-2"]

async def fetch_recommendations(orders):
    await asyncio.sleep(0.5)         # 故意比 time budget 慢
    return [f"rec-for-{order}" for order in orders]

async def page_data():
    # required：仍然设置 time budget，但失败或 timeout 都继续向外报告
    async with asyncio.timeout(0.2):
        orders = await fetch_orders()
    # optional：允许缺少这部分内容，但仍要有明确 time budget
    try:
        async with asyncio.timeout(0.2):
            recommendations = await fetch_recommendations(orders)
    except TimeoutError:
        # degradation：主动返回功能较少但仍可用的结果
        recommendations = None
    return {"orders": orders, "recommendations": recommendations}

async def failing_worker(name):
    await asyncio.sleep(0.05)
    raise RuntimeError(f"{name} 失败")

async def collect_errors():
    """收集errors，两个任务同时失败时，如何把多个错误一起保留下来，而不是只处理第一个。"""
    errors = []
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(failing_worker("A"))
            tg.create_task(failing_worker("B"))
    except* RuntimeError as group:
        # except* 在一组异常里按类型匹配，两个失败都被保留
        errors = sorted(str(error) for error in group.exceptions)
    return errors

async def main():
    print(await page_data())
    print(await collect_errors())

asyncio.run(main())