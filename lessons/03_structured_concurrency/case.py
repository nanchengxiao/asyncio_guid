import asyncio

async def worker(name, delay):
    """worker：只负责一件具体业务的小任务。"""
    try:
        print(f"[{name}] 开工")
        await asyncio.sleep(delay)
        if name == "payment":            # 故意让 payment 这个 worker 失败
            raise RuntimeError("余额不足")
        print(f"[{name}] 完成")
    finally:
        print(f"[{name}] cleanup：收尾自己的资源")

async def handle_order():
    # owner = handle_order 这层代码；lifecycle = async with 块的开始到结束
    async with asyncio.TaskGroup() as tg:       # structured concurrency 的边界
        # 三个 child Task，彼此是 sibling（同一个 owner、同一层级）
        inventory = tg.create_task(worker("inventory", 0.2))
        payment   = tg.create_task(worker("payment", 0.3))    # 会失败
        delivery  = tg.create_task(worker("delivery", 0.4))
    # 执行到这一行之前，整组必须已经 converge
    print("订单处理结束")   # 本例中这一行不会执行

async def main():
    try:
        await handle_order()
    except ExceptionGroup as eg:               # TaskGroup 用异常组向外报告失败
        print(f"调用者收到失败：{eg.exceptions[0]}")

asyncio.run(main())