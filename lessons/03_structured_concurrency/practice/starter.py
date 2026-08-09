async def run_group(worker_factories):
    # TODO：让一个父作用域统一拥有所有 worker。任一 worker 失败时，
    # 其余兄弟 Task 应收到取消请求，并在函数退出前有机会完成自己的清理。
    raise NotImplementedError
