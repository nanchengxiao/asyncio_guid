import asyncio

LIMIT = 3                          # concurrency limit

async def call_downstream(item, stats):
    stats["active"] += 1           # 记录真实行为，而不是搜索源码里的工具名
    stats["peak"] = max(stats["peak"], stats["active"])
    try:
        await asyncio.sleep(0.1)   # 真正占用稀缺 downstream resource 的调用
        return item * 10
    finally:
        # 即使失败或 cancellation，也不能让观测值永远多算一份 active 工作
        stats["active"] -= 1

async def process(item, semaphore, stats):
    # 准备、校验不占通行证；通行证只包围真正消耗 resource 的最小范围
    async with semaphore:
        return await call_downstream(item, stats)

async def main():
    semaphore = asyncio.Semaphore(LIMIT)  # 由本次 operation 创建并拥有
    stats = {"active": 0, "peak": 0}
    tasks = []
    async with asyncio.TaskGroup() as tg:
        for item in range(10):
            tasks.append(tg.create_task(process(item, semaphore, stats)))
    print([task.result() for task in tasks])
    print(f"active concurrency 峰值 peak = {stats['peak']}（limit = {LIMIT}）")
    # Semaphore 限制的是 active concurrency；等待中的 backlog 是另一个数量

asyncio.run(main())
