import asyncio

LIMIT = 3                          # concurrency limit
sem = asyncio.Semaphore(LIMIT)     # 有限数量的通行证
active = 0                         # 此刻正在占用稀缺 resource 的工作数
peak = 0                           # 观察期间出现过的最大值

async def call_downstream(item):
    global active, peak
    active += 1                    # 记录真实行为，而不是搜索源码里的工具名
    peak = max(peak, active)
    await asyncio.sleep(0.1)       # 真正占用稀缺 downstream resource 的调用
    active -= 1
    return item * 10

async def process(item):
    # 准备、校验不占通行证；通行证只包围真正消耗 resource 的最小范围
    async with sem:
        return await call_downstream(item)

async def main():
    results = []
    async with asyncio.TaskGroup() as tg:
        for item in range(10):
            results.append(tg.create_task(process(item)))
    print([t.result() for t in results])
    print(f"active concurrency 峰值 peak = {peak}（limit = {LIMIT}）")
    # Semaphore 限制的是 active concurrency；等待中的 backlog 是另一个数量

asyncio.run(main())
