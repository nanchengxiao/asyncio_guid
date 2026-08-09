"""异步上下文管理器与异步生成器示例。"""

import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator


@asynccontextmanager
async def managed_connection(name: str) -> AsyncIterator[str]:
    print(f"open: {name}")
    await asyncio.sleep(0.01)
    try:
        yield name
    finally:
        await asyncio.sleep(0.01)
        print(f"close: {name}")


async def stream_numbers(limit: int) -> AsyncIterator[int]:
    for value in range(limit):
        await asyncio.sleep(0.01)
        yield value


async def main() -> None:
    async with managed_connection("demo") as connection:
        async for value in stream_numbers(3):
            print(connection, value)


if __name__ == "__main__":
    asyncio.run(main())
