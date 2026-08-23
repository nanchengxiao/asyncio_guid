import asyncio
import time

async def fetch_user(user_id):
    print("[user] 开始")
    await asyncio.sleep(0.3)
    print("[user] 结束")
    return {"id": user_id}

async def fetch_orders(user_id):
    print("[orders] 开始")
    await asyncio.sleep(0.3)
    print("[orders] 结束")
    return [{"id": 101}]

async def dashboard_sequential(user_id):
    # 反例：两个连续 await，第二个直到第一个完成后才开始
    start = time.perf_counter()
    user = await fetch_user(user_id)
    orders = await fetch_orders(user_id)
    return time.perf_counter() - start, {"user": user, "orders": orders}

async def dashboard_concurrent(user_id):
    # 正例：两个 Task 同时存活，一段等待时 Event Loop 推进另一段
    start = time.perf_counter()
    user_task = asyncio.create_task(fetch_user(user_id))
    orders_task = asyncio.create_task(fetch_orders(user_id))
    user = await user_task        # 本例 Task 未完成，所以这里暂停并交回执行机会
    orders = await orders_task
    return time.perf_counter() - start, {"user": user, "orders": orders}

async def main():
    print("=== 顺序等待 ===")
    sequential_seconds, sequential_result = await dashboard_sequential(1)
    print("=== concurrency ===")
    concurrent_seconds, concurrent_result = await dashboard_concurrent(1)
    print(f"两种写法的业务结果相同：{sequential_result == concurrent_result}")
    print(concurrent_result)
    print(f"顺序等待 ≈ {sequential_seconds:.2f}s；"
          f"concurrency ≈ {concurrent_seconds:.2f}s")

asyncio.run(main())
