"""需要安装 aiohttp：python -m pip install aiohttp"""

import asyncio
import aiohttp


async def fetch_status(session: aiohttp.ClientSession, url: str) -> tuple[str, int]:
    async with session.get(url) as response:
        await response.read()
        return url, response.status


async def main() -> None:
    urls = ["https://example.com", "https://www.python.org"]
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        results = await asyncio.gather(*(fetch_status(session, url) for url in urls))
    for url, status in results:
        print(status, url)


if __name__ == "__main__":
    asyncio.run(main())
