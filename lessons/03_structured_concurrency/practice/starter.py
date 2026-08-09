async def run_group(worker_factories):
    # TODO：由一个父作用域拥有全部 worker。
    # 如果其中一个失败，其余 sibling 必须被取消，并在函数退出前完成各自的清理。
    raise NotImplementedError
