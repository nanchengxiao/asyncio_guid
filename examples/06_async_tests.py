"""运行：python -m unittest examples/06_async_tests.py -v"""

import asyncio
import unittest
from unittest.mock import AsyncMock


async def retry_once(operation, sleep=asyncio.sleep):
    try:
        return await operation()
    except TimeoutError:
        await sleep(0.01)
        return await operation()


class RetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_retries_after_timeout(self) -> None:
        operation = AsyncMock(side_effect=[TimeoutError("slow"), "ok"])
        sleep = AsyncMock()

        result = await retry_once(operation, sleep=sleep)

        self.assertEqual(result, "ok")
        self.assertEqual(operation.await_count, 2)
        sleep.assert_awaited_once_with(0.01)


if __name__ == "__main__":
    unittest.main()
