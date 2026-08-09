async def load_profiles(ids, blocking_loader, *, limit):
    # TODO: keep the event loop responsive while calling the blocking loader,
    # and cap concurrent calls into that loader.
    raise NotImplementedError
