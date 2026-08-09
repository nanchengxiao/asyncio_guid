async def fetch_json_batch(urls, *, connector_limit):
    # TODO：复用一个 aiohttp ClientSession，并创建 limit=connector_limit 的
    # TCPConnector；返回的 JSON 结果顺序必须与输入 URL 顺序一致。
    raise NotImplementedError
