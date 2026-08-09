import asyncio

import pytest

from course_testing import load_target

m = load_target(__file__)


class FastSource:
    def __init__(self, count):
        self.count = count
        self.produced = 0
        self.allow_processing = asyncio.Event()

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for i in range(self.count):
            self.produced += 1
            yield i


@pytest.mark.asyncio
async def test_bounded_queue_applies_backpressure():
    source = FastSource(20)
    started = asyncio.Event()
    release = asyncio.Event()

    async def handle(item):
        started.set()
        await release.wait()
        return item

    task = asyncio.create_task(m.run_pipeline(source, handle, queue_size=2, workers=1))
    await started.wait()
    await asyncio.sleep(0.02)
    # 1 个 item 正在处理，Queue 最多缓存 2 个；producer 还可能已经取到
    # 下一个 item，并在 queue.put() 处等待，因此 produced 最多允许到 4。
    assert source.produced <= 4
    release.set()
    results = await task
    assert sorted(results) == list(range(20))
