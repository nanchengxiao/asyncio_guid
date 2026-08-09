from contextlib import contextmanager


@contextmanager
def managed_records(records, close_resource):
    """按需暴露 records，并在退出上下文时关闭资源。

    Lesson 00 会直接给出控制流骨架。这里的练习目标是把本课概念正确连接起来，
    而不是猜测某个没有讲过的语法。
    """

    iterator = iter(records)

    try:
        # TODO 1：
        # @contextmanager 会把这里 yield 的值绑定到下面的 stream：
        #
        #     with managed_records(...) as stream:
        #                                  ^^^^^^
        #
        # 请把 None 替换为“调用方应该按需逐条读取”的对象。
        yield None
    finally:
        # TODO 2：
        # 在退出 with 上下文时调用清理函数，并且只调用一次。
        pass
