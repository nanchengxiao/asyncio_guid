async def run_group(worker_factories):
    # TODO: one parent scope owns every worker. If one fails, siblings must be
    # cancelled and allowed to run their cleanup before this function exits.
    raise NotImplementedError
