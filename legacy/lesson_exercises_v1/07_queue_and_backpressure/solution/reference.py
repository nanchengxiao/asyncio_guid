import asyncio


async def run_pipeline(source, handle, *, queue_size, workers):
    queue = asyncio.Queue(maxsize=queue_size)
    sentinel = object()
    results = []

    async def producer():
        async for item in source:
            await queue.put(item)
        for _ in range(workers):
            await queue.put(sentinel)

    async def consumer():
        while True:
            item = await queue.get()
            try:
                if item is sentinel:
                    return
                results.append(await handle(item))
            finally:
                queue.task_done()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(producer())
        for _ in range(workers):
            tg.create_task(consumer())
    return results
