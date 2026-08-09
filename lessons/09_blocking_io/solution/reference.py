import asyncio


async def load_profiles(ids, blocking_loader, *, limit):
    semaphore = asyncio.Semaphore(limit)

    async def load(item_id):
        async with semaphore:
            return await asyncio.to_thread(blocking_loader, item_id)

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(load(item_id)) for item_id in ids]
    return [task.result() for task in tasks]
