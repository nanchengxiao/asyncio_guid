# Lesson 00 — Python foundation

## 本节目标

学完本节，你应该能够：

- 区分 iterable、iterator 与 generator
- 解释 `yield` 的“产出 + 暂停 + 恢复”
- 理解“惰性（lazy）”为什么是“需要一个才产生一个”
- 用 `with` / context manager 表达资源的使用范围
- 说明 `finally` 为什么适合做必须执行的清理

## 进入本课前

只需要普通 Python 基础：函数、`for` 循环、列表/字典、异常、`try`/`except` 的基本写法。

**不需要提前知道 asyncio。** coroutine（协程）、Task、Event Loop、cancellation 会在后续课程正式解释。

## 为什么需要学习它

后面的异步代码会不断遇到两个问题：**一段工作可以暂停后继续**，以及**工作提前结束时资源仍必须清理**。

这一课先用普通 Python 的 generator、`finally` 和 context manager 建立这两个直觉。这样后面学习 asyncio 时是在理解已有模型，而不是只记“这里应该写哪个 API”。

## 核心理论

### 1. iterable 和 iterator

```python
numbers = [10, 20, 30]
it = iter(numbers)

next(it)  # 10
next(it)  # 20
```

- **iterable（可迭代对象）**：里面有一批内容，可以“开始一次遍历”。列表就是 iterable。
- **iterator（迭代器）**：已经处在某次遍历过程中，并且记得自己走到哪里。

可以把它们想成：

```text
iterable：一本可以开始阅读的书
iterator：夹着书签、记得读到哪一页的阅读过程
```

`iter(numbers)` 得到 iterator，`next(it)` 让它向前走一步。`for` 循环背后也在做类似的事情。

### 2. generator 和 `yield`

**generator（生成器）是一种方便创建 iterator 的方式。**

```python
def batches():
    print("A")
    yield [1, 2]
    print("B")
    yield [3, 4]
```

这里的 `yield` 可以先记成一句话：

> **产出一个值，然后把函数暂停在这里；下一次继续时，从这里后面接着执行。**

```python
g = batches()  # 这里只创建 generator，还没有打印 A
next(g)        # 打印 A，得到 [1, 2]，暂停
next(g)        # 从上次位置继续，打印 B，得到 [3, 4]
```

这就是本课要建立的“暂停后从原位置恢复”直觉。

### 3. 什么叫“惰性（lazy）”

假设有 100 万条记录：

- 方案 A：先把 100 万条全部读取出来；
- 方案 B：调用者需要下一条时，才读取下一条。

方案 B 就叫**惰性处理**：

> **不提前把所有工作做完，而是需要一个才产生/读取一个。**

如果调用者只需要前 3 条，后面的记录甚至不必读取。本课练习说的“逐条按需产生记录”就是这个意思。

### 4. resource、acquire、release

这里的 **resource（资源）** 可以是打开的文件、网络连接、数据库连接等需要正确关闭/归还的对象。

工程文档常把资源生命周期写成：

```text
acquire  →  use  →  release
获得资源    使用      释放资源
```

例如：

```text
open() → read() → close()
```

所以以后看到 acquire / release，不需要把它们当成特殊 Python 语法；它们只是“获得资源 / 释放资源”的工程术语。

### 5. 为什么需要 `finally`

如果资源必须关闭，仅仅把 `close()` 放在函数最后并不可靠：中途异常或提前 `return` 时，最后那行可能执行不到。

```python
resource = open_resource()
try:
    use(resource)
finally:
    resource.close()
```

`finally` 表示：**无论 `try` 里面正常结束、提前返回还是发生异常，离开这里前都要执行这段收尾代码。**

这里的 **cleanup** 就是“清理/收尾”，例如关闭文件、归还连接。

### 6. `with` 和 context manager

**context manager（上下文管理器）**用来表达“进入一个资源使用范围，离开时自动收尾”。

```python
with open("data.txt") as f:
    data = f.read()
```

这里从 `with` 开始到缩进块结束，就是一个**可见的生命周期边界**：从代码外观上就能看出资源在哪开始使用、到哪一定结束。

常说 `with` 是“**语法糖（syntactic sugar）**”，意思只是：

> 用更容易读、更不容易写错的语法，表达原本也能手工写出的逻辑。

“语法糖”不代表资源关闭不重要，恰恰相反，`with` 是把资源规则写得更清楚。

本课练习使用标准库的 `@contextmanager`：

```python
from contextlib import contextmanager

@contextmanager
def managed():
    resource = open_resource()
    try:
        yield resource
    finally:
        resource.close()
```

你现在不需要研究 `@contextmanager` 的内部实现，只要理解：`yield` 前负责进入和获得资源，`yield` 后的 `finally` 负责退出和清理。

## 脑内执行模型

```text
进入 with
   ↓
获得资源
   ↓
需要一条 → 产生一条 → 需要一条 → 再产生一条
   ↓
调用者可能提前停止
   ↓
离开 with → finally → 关闭资源
```

## 常见误解

- **误区：** generator function 一调用就执行到第一个 `yield`。实际调用时只创建 generator，第一次 `next()` 才进入函数体。
- **误区：** 只有异常时 `finally` 才运行。正常结束和提前 `return` 也会进入 `finally`。
- **误区：** “惰性”就是更快。它主要表示“不提前做不需要的工作、不提前占用全部内存”。
- **误区：** `with` 是语法糖，所以资源关闭无所谓。语法糖只是写法更清晰，不会改变资源必须正确释放这件事。

## 本节规则总结

1. iterable 表示“可以开始遍历”，iterator 表示“正在遍历并记得位置”。
2. `yield` 会产出值并暂停 generator，下一次从原位置继续。
3. “惰性”就是按需产生：需要一个才处理一个。
4. 必须执行的 cleanup 放进 `finally`。
5. `with` 让 acquire / use / release 处在一个清楚可见的生命周期范围里。

## 关键问题

1. `batches()` 和第一次 `next(g)` 分别会发生什么？
2. `yield` 与 `return` 最大的执行流程区别是什么？
3. iterable 与 iterator 为什么不是同一个概念？
4. 如果只需要前 3 条记录，为什么按需读取可能比先读完全部更合适？
5. 为什么 `finally` 比“在函数最后写 close()”更可靠？
6. 为什么 `with` 的缩进代码块可以看作资源生命周期边界？

## 场景命题

实现一个 `managed_records` 上下文管理器。

它接收一批输入记录，但**不要提前把全部记录复制或读取出来**；调用者需要下一条时，再提供下一条。调用者可能只读前几条就停止，但离开 `with` 时资源必须关闭。

## 验收

测试会确认：

1. 记录按输入顺序逐条产生；
2. 实现不会为了开始遍历而提前读完全部记录；
3. 无论正常结束还是提前停止，离开 `with` 时都会执行一次资源清理。

仓库参考实现：

```bash
uv run pytest lessons/00_python_foundation/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/00_python_foundation/tests -v --learner
```
