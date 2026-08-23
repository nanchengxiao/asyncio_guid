import asyncio
import time

THREAD_LIMIT = 2                  # thread pool 同样是有限 resource
thread_sem = asyncio.Semaphore(THREAD_LIMIT)

def legacy_loader(profile_id):
    """旧 SDK 的普通同步函数：内部会长时间等待（blocking I/O）。"""
    time.sleep(0.3)
    return {"profile": profile_id, "data": "..."}

async def load_profile(profile_id):
    # to_thread 把同步函数交给 worker thread；当前 Task 只负责 async 等待结果
    async with thread_sem:
        return await asyncio.to_thread(legacy_loader, profile_id)

async def heartbeat():
    for _ in range(6):
        print("tick：Event Loop 仍在推进其他 Task")
        await asyncio.sleep(0.1)

async def main():
    hb = asyncio.create_task(heartbeat())
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(load_profile(i)) for i in (1, 2, 3)]
    profiles = [t.result() for t in tasks]
    print(profiles)
    print(f"loader 线程并发上限 = {THREAD_LIMIT}；blocking 调用期间 heartbeat 未被拖住")
    await hb

asyncio.run(main())
