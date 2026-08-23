import asyncio

class RecommendationsUnavailable(Exception):
    """Recommendations 这条 optional dependency 的已知业务失败。"""

async def fetch_user():
    print("[user] 开始")
    await asyncio.sleep(0.1)
    print("[user] 完成")
    return {"id": 7}

async def fetch_orders():
    print("[orders] 开始")
    await asyncio.sleep(0.15)
    print("[orders] 完成")
    return [{"id": 101}, {"id": 102}]

async def fetch_account(user):
    print("[account] user 已就绪，开始")
    await asyncio.sleep(0.1)
    print("[account] 完成")
    return {"user_id": user["id"], "balance": 100}

async def fetch_recommendations(orders):
    print(f"[recommendations] {len(orders)} 条 orders 已就绪，开始")
    await asyncio.sleep(0.2)
    raise RecommendationsUnavailable("推荐服务失败")

async def user_account_branch():
    """一条依赖链：user → account。"""
    user = await fetch_user()
    account = await fetch_account(user)       # edge：account 依赖 user
    return user, account

async def orders_recommendations_branch():
    """另一条依赖链：orders → recommendations。"""
    orders = await fetch_orders()
    try:
        recommendations = await fetch_recommendations(orders)
    except RecommendationsUnavailable:
        print("[recommendations] optional 失败，执行 degradation")
        recommendations = None                # degradation：允许缺少结果
    return orders, recommendations

async def aggregate():
    async with asyncio.TaskGroup() as tg:
        # 两条独立依赖链同时开始；每条链内部用 await 表达自己的 edge
        user_branch = tg.create_task(user_account_branch())
        orders_branch = tg.create_task(orders_recommendations_branch())
    user, account = user_branch.result()
    orders, recommendations = orders_branch.result()
    return {
        "user": user,                            # required
        "orders": orders,                        # required
        "account": account,                      # required
        "recommendations": recommendations,      # optional
    }

async def main():
    result = await aggregate()
    if result["recommendations"] is None:
        print("degradation：缺少推荐内容，页面仍返回")
    print(result)

asyncio.run(main())
