"""比较直接阻塞事件循环和把阻塞调用移到线程。"""

import asyncio
import time


def blocking_operation(seconds: float) -> str:
    time.sleep(seconds)
    return f"blocked for {seconds:.2f}s"


async def heartbeat(label: str, count: int = 5) -> None:
    for index in range(count):
        print(f"{label}: {index}")
        await asyncio.sleep(0.05)


async def main() -> None:
    beat = asyncio.create_task(heartbeat("heartbeat"))

    # 推荐：把阻塞函数放入工作线程。
    result = await asyncio.to_thread(blocking_operation, 0.2)
    print(result)

    await beat


if __name__ == "__main__":
    asyncio.run(main())
