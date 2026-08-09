async def run_required(operation, timeout_seconds):
    # TODO: enforce a time budget around the required operation.
    raise NotImplementedError


async def collect_parallel_failures(*operations):
    # TODO: run sibling operations as one structured group and return the
    # ExceptionGroup to the caller when multiple failures happen.
    raise NotImplementedError
