"""Lesson 00 的最小可运行实验。

运行方式：
    uv run python lessons/00_python_foundation/experiments.py

建议每一段都先预测输出顺序，再实际运行。
"""

from contextlib import contextmanager


def experiment_iter_and_next():
    print("\n=== 1. 从可迭代对象得到迭代器，再逐步 next ===")
    numbers = [10, 20]
    iterator = iter(numbers)

    print("原始数据：", numbers)
    print("第 1 次 next：", next(iterator))
    print("第 2 次 next：", next(iterator))

    try:
        next(iterator)
    except StopIteration:
        print("第 3 次 next：StopIteration（没有下一项了）")


def experiment_generator_pause_resume():
    print("\n=== 2. generator 的暂停与恢复 ===")

    def demo():
        print("生成器：A")
        yield 1
        print("生成器：B")
        yield 2
        print("生成器：C")

    generator = demo()
    print("调用方：generator object 已创建，但函数体还没运行")

    print("调用方：第 1 次 next ->", next(generator))
    print("调用方：第 2 次 next ->", next(generator))

    try:
        next(generator)
    except StopIteration:
        print("调用方：第 3 次 next -> StopIteration")


def experiment_finally():
    print("\n=== 3. 离开 try 前会执行 finally ===")

    try:
        print("try：正在工作")
        print("try：准备离开")
    finally:
        print("finally：执行收尾")


def experiment_contextmanager():
    print("\n=== 4. @contextmanager 的进入与退出 ===")

    @contextmanager
    def managed():
        print("管理器：yield 之前，属于进入阶段")
        try:
            yield "resource"
        finally:
            print("管理器：finally，属于退出阶段")

    print("调用方：进入 with 之前")
    with managed() as resource:
        print("调用方：with 内部，拿到 ->", resource)
    print("调用方：离开 with 之后")


def main():
    experiment_iter_and_next()
    experiment_generator_pause_resume()
    experiment_finally()
    experiment_contextmanager()


if __name__ == "__main__":
    main()
