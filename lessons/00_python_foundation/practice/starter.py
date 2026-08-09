from contextlib import contextmanager


@contextmanager
def managed_records(records, close_resource):
    # TODO: expose records lazily and guarantee close_resource() exactly once
    # when the context ends, including early consumer exit or exception.
    raise NotImplementedError
