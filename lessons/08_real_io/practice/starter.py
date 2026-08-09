async def fetch_json_batch(urls, *, connector_limit):
    # TODO：复用一个 aiohttp ClientSession，并使用 limit=connector_limit 的 TCPConnector。
    # 返回结果时保持与输入 urls 相同的顺序。
    raise NotImplementedError
