import asyncio


async def run_group(worker_factories):
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(factory()) for factory in worker_factories]
    return [task.result() for task in tasks]
