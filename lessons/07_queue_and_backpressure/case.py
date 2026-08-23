import asyncio

WORKERS = 2
SENTINEL = object()                        # 结束标记：双方约定的特殊值

async def source():
    for item in range(1, 7):
        await asyncio.sleep(0.01)          # 取下一条本身可能需要等待
        yield item

async def producer(queue):
    # 逐项读取 AsyncIterable；不要先把数据源全部读完再入队
    async for item in source():
        print(f"producer 尝试 put {item}")
        await queue.put(item)              # Queue 已满时这里等待 → backpressure
        print(f"producer 完成 put {item}（Queue 中 {queue.qsize()} 条）")
    for _ in range(WORKERS):
        await queue.put(SENTINEL)          # 每个 worker 一个结束标记

async def worker(queue, name):
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
    queue = asyncio.Queue(maxsize=2)        # 由本条 pipeline 创建并拥有
    async with asyncio.TaskGroup() as tg:
        for worker_number in range(WORKERS):
            tg.create_task(worker(queue, f"worker-{worker_number}"))
        await producer(queue)
        await queue.join()                 # drain：已接收的工作全部处理完
    print("pipeline 结束")

asyncio.run(main())
