import asyncio

import aiohttp


async def fetch_json_batch(urls, *, connector_limit):
    connector = aiohttp.TCPConnector(limit=connector_limit)
    async with aiohttp.ClientSession(connector=connector) as session:
        async def fetch(url):
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()

        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(fetch(url)) for url in urls]
        return [task.result() for task in tasks]
