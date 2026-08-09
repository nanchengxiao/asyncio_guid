async def load_profiles(ids, blocking_loader, *, limit):
    # TODO：调用同步阻塞 loader 时仍要让 Event Loop 保持响应；同时限制
    # 工作线程中并发调用 blocking_loader 的数量。
    raise NotImplementedError
