async def fetch_json_batch(urls, *, connector_limit):
    # TODO: use one aiohttp ClientSession and a TCPConnector whose limit is
    # connector_limit. Return JSON responses in input order.
    raise NotImplementedError
