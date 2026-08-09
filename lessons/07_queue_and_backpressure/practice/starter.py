async def run_pipeline(source, handle, *, queue_size, workers):
    # TODO：通过有容量上限的 Queue 和固定数量的 worker 逐项消费 source。
    # 不要先把整个 source 一次性读取并保存下来。
    raise NotImplementedError
