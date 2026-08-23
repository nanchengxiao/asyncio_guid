import asyncio

from aiohttp import ClientSession, TCPConnector, web

async def start_local_server():
    """本地临时 server：不依赖外部网站，方便观察 active request。"""
    stats = {"active": 0, "peak": 0}

    async def handler(request):
        stats["active"] += 1
        stats["peak"] = max(stats["peak"], stats["active"])
        await asyncio.sleep(0.1)               # server 处理 request 也需要时间
        stats["active"] -= 1
        return web.json_response({"path": request.path})

    app = web.Application()
    app.router.add_get("/{path:.*}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)  # 端口 0：让系统分配可用端口
    await site.start()
    port = runner.addresses[0][1]
    return runner, port, stats

async def fetch_one(session, url):
    # 拿到 response 不代表 body 已读完；读取 body 本身也可能需要等待
    async with session.get(url) as response:
        data = await response.json()
    return url, data

async def main():
    runner, port, server_stats = await start_local_server()
    urls = [f"http://127.0.0.1:{port}/data/{i}" for i in range(6)]
    connector = TCPConnector(limit=2)           # connection pool 的容量边界
    results = []
    # 一批相关 request 复用同一个 ClientSession，由它复用有限 connection
    async with ClientSession(connector=connector) as session:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(fetch_one(session, url)) for url in urls]
        results = [task.result() for task in tasks]  # 顺序与输入 URL 顺序一致
    for url, data in results:
        print(url, data)
    print(f"server 观察到同时处理的 request 峰值 = {server_stats['peak']}"
          f"（connection pool limit=2，远少于 Task 数量）")
    await runner.cleanup()

asyncio.run(main())
