import asyncio


async def fetch_many(items, fetch_one, limit):
    semaphore = asyncio.Semaphore(limit)

    async def run(item):
        async with semaphore:
            return await fetch_one(item)

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(run(item)) for item in items]
    return [task.result() for task in tasks]
