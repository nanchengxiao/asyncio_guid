from contextlib import contextmanager

def source():
    """generator function：按需产生数据，请求一条才读取一条。"""
    for number in (1, 2, 3):
        print(f"produce {number}")
        yield number

def close_resource():
    """resource 的收尾动作，稍后作为 callback 传给 context manager。"""
    print("closed：resource 收尾")

@contextmanager
def managed_records(records, cleanup_callback):
    try:
        yield iter(records)      # yield 前：进入阶段；yield 后：退出阶段
    finally:
        cleanup_callback()       # 无论正常结束还是抛异常，离开 with 都会收尾

def main():
    records_generator = source()
    # 调用 source() 只是创建 generator object，函数体还没有运行
    with managed_records(records_generator, close_resource) as records:
        first = next(records)    # lazy：需要 1 条，只读取 1 条
        print(f"got {first}")
        # 不要在这里 list(records)：那会立即把剩余内容全部读完
    # 离开 with 后，close_resource() 已经执行

main()
