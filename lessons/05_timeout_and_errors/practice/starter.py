async def run_required(operation, timeout_seconds):
    # TODO：为这个必需操作设置明确的时间预算。
    raise NotImplementedError


async def collect_parallel_failures(*operations):
    # TODO：把这些兄弟操作作为一个结构化并发组运行；如果同时出现多个失败，
    # 应把完整的 ExceptionGroup 继续交给调用者，而不是只保留第一个异常。
    raise NotImplementedError
