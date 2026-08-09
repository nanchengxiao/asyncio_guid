async def load_profiles(ids, blocking_loader, *, limit):
    # TODO：调用 blocking_loader 时保持事件循环可响应，
    # 同时限制进入这个同步阻塞函数的并发调用数量。
    raise NotImplementedError
