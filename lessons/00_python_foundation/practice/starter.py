from contextlib import contextmanager


@contextmanager
def managed_records(records, close_resource):
    # TODO：按需逐条提供 records，并保证离开 with 时恰好调用一次
    # close_resource()；即使调用者提前停止或发生异常，也必须完成清理。
    raise NotImplementedError
