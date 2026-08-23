import asyncio

import pytest

from course_testing import load_target

m = load_target(__file__)


@pytest.mark.asyncio
async def test_cancellation_propagates_after_cleanup():
    cleanup_calls = 0
    first = asyncio.Event()
    release = asyncio.Event()

    async def send_chunk(chunk):
        first.set()
        await release.wait()

    async def cleanup():
        nonlocal cleanup_calls
        cleanup_calls += 1

    task = asyncio.create_task(m.upload_chunks([b"a", b"b"], send_chunk, cleanup))
    await first.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cleanup_calls == 1
