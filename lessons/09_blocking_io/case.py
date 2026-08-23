import asyncio
import time

THREAD_LIMIT = 2                  # thread pool 同样是有限 resource

def legacy_loader(profile_id):
    """旧 SDK 的普通同步函数：内部会长时间等待（blocking I/O）。"""
    print(f"[loader {profile_id}] worker thread 开始")
    time.sleep(0.3)
    print(f"[loader {profile_id}] worker thread 结束")
    return {"profile": profile_id, "data": "..."}

async def load_profile(profile_id, thread_semaphore):
    # to_thread 把同步函数交给 worker thread；当前 Task 只负责 async 等待结果
    async with thread_semaphore:
        return await asyncio.to_thread(legacy_loader, profile_id)

async def heartbeat():
    for _ in range(6):
        print("tick：Event Loop 仍在推进其他 Task")
        await asyncio.sleep(0.1)

async def main():
    thread_semaphore = asyncio.Semaphore(THREAD_LIMIT)
    tasks = []
    async with asyncio.TaskGroup() as tg:
        tg.create_task(heartbeat())
        for profile_id in (1, 2, 3):
            tasks.append(tg.create_task(load_profile(profile_id, thread_semaphore)))
    profiles = [task.result() for task in tasks]
    print(profiles)
    print(f"loader 线程并发上限 = {THREAD_LIMIT}；blocking 调用期间 heartbeat 未被拖住")

asyncio.run(main())
