import asyncio

from aiohttp import web
import pytest

from course_testing import load_target

m = load_target(__file__)


@pytest.mark.asyncio
async def test_local_http_and_connection_pool_limit(unused_tcp_port):
    active = 0
    peak = 0
    lock = asyncio.Lock()

    async def handler(request):
        nonlocal active, peak
        async with lock:
            active += 1
            peak = max(peak, active)
        await asyncio.sleep(0.02)
        async with lock:
            active -= 1
        return web.json_response({"id": int(request.match_info["id"])})

    app = web.Application()
    app.router.add_get('/items/{id}', handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', unused_tcp_port)
    await site.start()
    try:
        urls = [f'http://127.0.0.1:{unused_tcp_port}/items/{i}' for i in range(6)]
        result = await m.fetch_json_batch(urls, connector_limit=2)
    finally:
        await runner.cleanup()

    assert result == [{"id": i} for i in range(6)]
    assert peak == 2
