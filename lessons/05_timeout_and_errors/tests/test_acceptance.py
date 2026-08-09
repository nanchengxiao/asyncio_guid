import asyncio

import pytest

from course_testing import load_target

m = load_target(__file__)


@pytest.mark.asyncio
async def test_required_timeout():
    async def slow():
        await asyncio.sleep(1)

    with pytest.raises(TimeoutError):
        await m.run_required(slow, 0.02)


@pytest.mark.asyncio
async def test_parallel_failures_are_preserved():
    async def bad_value():
        raise ValueError("v")

    async def bad_runtime():
        raise RuntimeError("r")

    group = await m.collect_parallel_failures(bad_value, bad_runtime)
    assert isinstance(group, ExceptionGroup)
    flat = list(group.exceptions)
    assert any(isinstance(e, ValueError) for e in flat)
    assert any(isinstance(e, RuntimeError) for e in flat)
