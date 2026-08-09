import asyncio


async def run_required(operation, timeout_seconds):
    async with asyncio.timeout(timeout_seconds):
        return await operation()


async def collect_parallel_failures(*operations):
    gate = asyncio.Event()

    async def wrapped(operation):
        await gate.wait()
        return await operation()

    captured = None
    try:
        async with asyncio.TaskGroup() as tg:
            for operation in operations:
                tg.create_task(wrapped(operation))
            gate.set()
    except* Exception as group:
        captured = group
    return captured
