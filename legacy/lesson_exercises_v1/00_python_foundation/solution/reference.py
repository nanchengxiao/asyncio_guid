from contextlib import contextmanager


@contextmanager
def managed_records(records, close_resource):
    try:
        yield iter(records)
    finally:
        close_resource()
