async def run_pipeline(source, handle, *, queue_size, workers):
    # TODO: consume source incrementally through a bounded queue and fixed
    # workers. Do not materialize the whole source first.
    raise NotImplementedError
