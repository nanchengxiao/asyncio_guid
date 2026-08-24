from contextlib import contextmanager

def source():
    """按需产生数据，请求一条才给一条。"""
    for number in (1, 2, 3):
        print(f'produce {number}')
        yield number

def close_resource():
    """资源回收，稍后作为 callback（把一个函数当作值传进去，等到需要时再调用它） 传给传给 context manager。"""
    print("closed: 资源回收") # 这里只是打印表示

@contextmanager
def managed_records(records, cleanup_callback):
    try:
        yield iter(records)
    finally:
        cleanup_callback()

def main():
    records_generator = source()
    # 调用source() 只是创建 generator object（生成器对象），generator function（生成器函数）还没有运行
    with managed_records(records=records_generator, cleanup_callback=close_resource) as records:
        first = next(records)
        print(f'got {first}')

main()

