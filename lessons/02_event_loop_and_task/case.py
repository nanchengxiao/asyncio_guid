import asyncio
import time

async def fetch_user(user_id):
    await asyncio.sleep(0.3)
    return {"id": user_id}

async def fetch_orders(user_id):
    await asyncio.sleep(0.3)
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
    user = await user_task        # 走到 await 才把执行机会交回 Event Loop
    orders = await orders_task
    return time.perf_counter() - start, {"user": user, "orders": orders}

async def main():
    seq_seconds, _ = await dashboard_sequential(1)
    conc_seconds, result = await dashboard_concurrent(1)
    print(result)
    print(f"顺序等待 ≈ {seq_seconds:.2f}s；concurrency ≈ {conc_seconds:.2f}s")

asyncio.run(main())
