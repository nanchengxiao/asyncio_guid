import asyncio

import pytest

from course_testing import load_target

m = load_target(__file__)


@pytest.mark.asyncio
async def test_failure_cancels_sibling_and_waits_for_cleanup():
    events = []
    blocker = asyncio.Event()

    async def failing():
        await asyncio.sleep(0)
        raise ValueError("boom")

    async def sibling():
        try:
            await blocker.wait()
        except asyncio.CancelledError:
            events.append("cancelled")
            raise
        finally:
            events.append("cleanup")

    with pytest.raises(ExceptionGroup) as exc:
        await m.run_group([failing, sibling])
    assert any(isinstance(e, ValueError) for e in exc.value.exceptions)
    assert events == ["cancelled", "cleanup"]
