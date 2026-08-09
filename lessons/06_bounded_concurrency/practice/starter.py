async def fetch_many(items, fetch_one, limit):
    # TODO：保持输入顺序和有效并发，同时保证任意时刻进入 fetch_one 的调用数
    # 都不超过 `limit`。
    raise NotImplementedError
