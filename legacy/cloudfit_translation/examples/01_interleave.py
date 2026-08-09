"""展示两个协程如何在显式让出点交错执行。"""

import asyncio


async def worker(name: str, steps: int = 4) -> None:
    for step in range(steps):
        print(f"{name}: step={step}")
        await asyncio.sleep(0)


async def main() -> None:
    await asyncio.gather(worker("alpha"), worker("beta"))


if __name__ == "__main__":
    asyncio.run(main())




