async def run_required(operation, timeout_seconds):
    # TODO：为这个 required operation 设置明确的超时时间预算。
    raise NotImplementedError


async def collect_parallel_failures(*operations):
    # TODO：把这些 sibling operation 作为一个 structured group 并发运行；
    # 当多个任务失败时，让 ExceptionGroup 继续交给调用方处理。
    raise NotImplementedError
