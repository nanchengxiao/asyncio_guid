import asyncio

WORKERS = 2
SENTINEL = object()                        # 结束标记：双方约定的特殊值
queue = asyncio.Queue(maxsize=2)           # maxsize 给 backlog 建边界

async def source():
    for i in range(1, 7):
        await asyncio.sleep(0.01)          # 取下一条本身可能需要等待
        yield i

async def producer():
    # 逐项读取 AsyncIterable；不要先把数据源全部读完再入队
    async for item in source():
        await queue.put(item)              # Queue 已满时这里等待 → backpressure
        print(f"put {item}（等待中 {queue.qsize()} 条）")
    for _ in range(WORKERS):
        await queue.put(SENTINEL)          # 每个 worker 一个结束标记

async def worker(name):
    while True:
        item = await queue.get()
        try:
            if item is SENTINEL:           # worker 自己识别并干净退出
                break
            await asyncio.sleep(0.1)       # 处理这一条 item
            print(f"[{name}] 完成 {item}")
        finally:
            queue.task_done()              # get() 只表示取走，完成后才标记

async def main():
    async with asyncio.TaskGroup() as tg:
        for n in range(WORKERS):
            tg.create_task(worker(f"worker-{n}"))
        await producer()
        await queue.join()                 # drain：已接收的工作全部处理完
    print("pipeline 结束")

asyncio.run(main())
