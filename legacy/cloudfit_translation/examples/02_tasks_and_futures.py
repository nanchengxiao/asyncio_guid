"""演示协程对象、Task 和手工 Future 的区别。"""

import asyncio
from collections.abc import Callable
from typing import Any


async def delayed_value(value: int, delay: float) -> int:
    await asyncio.sleep(delay)
    return value


async def callback_bridge(register: Callable[[Callable[..., None]], Any]) -> str:
    loop = asyncio.get_running_loop()
    future: asyncio.Future[str] = loop.create_future()

    def done(value: str) -> None:
        if not future.done():
            future.set_result(value)

    register(done)
    return await future


async def main() -> None:
    coroutine_object = delayed_value(10, 0.05)
    task = asyncio.create_task(delayed_value(20, 0.02), name="value-20")

    first = await coroutine_object
    second = await task
    print(first, second)

    def register(callback: Callable[[str], None]) -> None:
        asyncio.get_running_loop().call_later(0.01, callback, "from callback")

    print(await callback_bridge(register))


if __name__ == "__main__":
    asyncio.run(main())
