import asyncio

async def fetch_order(order_id):
    print(f"fetch_order({order_id}) 函数体开始执行")
    await asyncio.sleep(0.2)
    return {"id": order_id, "customer_id": 7}

async def fetch_customer(customer_id):
    print(f"fetch_customer({customer_id}) 函数体开始执行")
    await asyncio.sleep(0.2)
    return {"id": customer_id, "name": "Ada"}

async def main():
    coro = fetch_order(1)
    # 调用 coroutine function 只得到 coroutine object，上面还没打印任何东西
    order = await coro
    # data dependency：customer 查询必须拿到 order["customer_id"] 才能开始
    customer = await fetch_customer(order["customer_id"])
    print(order, customer)

asyncio.run(main())
