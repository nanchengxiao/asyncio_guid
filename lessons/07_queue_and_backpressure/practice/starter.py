async def run_pipeline(source, handle, *, queue_size, workers):
    # TODO：通过有界队列和固定数量的 worker 逐步消费 source。
    # 不要先把整个 source 一次性读入内存。
    raise NotImplementedError
