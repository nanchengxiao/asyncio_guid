import asyncio
from contextlib import asynccontextmanager

from aiohttp import ClientSession, TCPConnector, web

@asynccontextmanager
async def local_server():
    """本地临时 server：不依赖外部网站，方便观察 active request。"""
    stats = {"active": 0, "peak": 0}

    async def handler(request):
        stats["active"] += 1
        stats["peak"] = max(stats["peak"], stats["active"])
        try:
            await asyncio.sleep(0.1)           # server 处理 request 也需要时间
            return web.json_response({"path": request.path})
        finally:
            stats["active"] -= 1              # 失败或 cancellation 时也修正观测值

    app = web.Application()
    app.router.add_get("/{path:.*}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        site = web.TCPSite(runner, "127.0.0.1", 0)  # 0：让系统分配可用端口
        await site.start()
        port = runner.addresses[0][1]
        yield port, stats                      # server 已可用，交给 client 测试
    finally:
        await runner.cleanup()                 # 启动后任一路径都停止本地 server
        print("local server cleanup：完成")

async def fetch_one(session, url):
    # 拿到 response 不代表 body 已读完；读取 body 本身也可能需要等待
    async with asyncio.timeout(1.0):            # 复用 Lesson 05 的 time budget
        async with session.get(url) as response:
            response.raise_for_status()         # 4xx / 5xx 不能伪装成成功结果
            data = await response.json()
    return url, data

async def main():
    async with local_server() as (port, server_stats):
        urls = [f"http://127.0.0.1:{port}/data/{number}" for number in range(6)]
        connector = TCPConnector(limit=2)       # connection pool 的容量边界
        # 一批相关 request 复用同一个 ClientSession，由它复用有限 connection
        async with ClientSession(connector=connector) as session:
            async with asyncio.TaskGroup() as tg:
                tasks = [tg.create_task(fetch_one(session, url)) for url in urls]
            results = [task.result() for task in tasks]  # 与输入 URL 顺序一致
        for url, data in results:
            print(url, data)
        print(f"server 观察到同时处理的 request 峰值 = {server_stats['peak']}"
              f"（connection pool limit=2，远少于 Task 数量）")

asyncio.run(main())
