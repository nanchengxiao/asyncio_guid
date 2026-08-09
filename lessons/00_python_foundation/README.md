# Lesson 00 — Python foundation

## 本节目标

学完本节，你应该能够：

- 区分 iterable、iterator 与 generator
- 解释 `yield` 为什么能让函数暂停并从原处继续
- 用 `with` / context manager 表达资源的使用范围
- 说明 `finally` 为什么适合做必须执行的清理
- 理解“惰性（lazy）”为什么意味着“需要一个才产生一个”

## 进入本课前

只需要普通 Python 基础：函数、`for` 循环、列表/字典、异常、`try`/`except` 的基本写法。

**不需要提前知道任何 asyncio 概念。** coroutine、Task、Event Loop、cancellation 都会在后面的课程里正式解释。

## 为什么需要学习它

异步程序以后会大量遇到两件事：

1. 一段工作可以执行一会儿、暂停，之后再继续；
2. 一段工作可能提前结束，但已经打开的文件、连接等资源仍然必须关闭。

这一课先用普通 Python 的 generator、`finally` 和 context manager 建立这两个直觉。后面遇到 asyncio 的暂停、取消和资源清理时，你会是在已有模型上继续学习，而不是只记住“这里要写某个 API”。

## 核心理论

### 1. iterable 和 iterator 到底是什么

先看一个最普通的列表：

```python
numbers = [10, 20, 30]
```

这个列表是 **iterable（可迭代对象）**：意思是“它里面有一批东西，可以开始遍历”。

当你写：

```python
it = iter(numbers)
```

得到的是 **iterator（迭代器）**。可以把它理解成“一个正在遍历这批数据、而且记得自己走到哪里了的对象”。

```python
next(it)  # 10
next(it)  # 20
next(it)  # 30
```

每调用一次 `next(it)`，迭代器向前走一步。它之所以能继续，是因为它记得上一次的位置。

可以把两者想成：

```text
iterable：一本可以开始阅读的书
iterator：夹着书签、记得已经读到哪一页的阅读过程
```

`for x in numbers:` 背后也会先取得 iterator，再不断向它取下一个值。

### 2. generator 和 `yield`

**generator（生成器）是一种很方便的 iterator。**

```python
def batches():
    print("A")
    yield [1, 2]
    print("B")
    yield [3, 4]
```

这里的 `yield` 可以先理解为：

> **产出一个值，然后把函数暂停在这里。下一次继续时，从 `yield` 后面接着执行。**

调用：

```python
g = batches()
```

并不会立刻打印 `A`。它只是创建一个 generator object。

第一次：

```python
next(g)
```

执行过程是：

```text
打印 A
↓
yield [1, 2]
↓
把 [1, 2] 交给调用者
↓
暂停
```

第二次 `next(g)` 时，不会从函数第一行重新开始，而是从上次暂停的位置继续：

```text
从第一个 yield 后继续
↓
打印 B
↓
yield [3, 4]
↓
再次暂停
```

所以这一课真正想让你记住的是：**一个执行过程可以保存自己的当前位置和局部变量，稍后从原处恢复。**

### 3. 什么叫“惰性（lazy）”

假设有 100 万条记录。

一种做法是先把 100 万条全部读取到列表，再交给调用者；另一种做法是调用者要一条时才读取一条。

第二种就叫 **惰性（lazy）处理**：

> 不提前完成所有工作，而是“需要一个，才产生/读取一个”。

例如 generator 天然适合这种方式：

```python
def records():
    for row in source:
        yield row
```

如果调用者只取前 3 条就停止，那么后面的记录可以根本不读取。这就是本课练习里“惰性记录流”的意思；后文会直接说“逐条按需产生记录”，不要求你先懂这个术语。

### 4. 资源、acquire、use、release 是什么

这里说的**资源（resource）**，可以是：

- 一个打开的文件；
- 一个网络连接；
- 一个数据库连接；
- 一个需要显式关闭的客户端对象。

常见生命周期有三步：

```text
acquire  →  use  →  release
获得资源    使用      释放
```

例如文件：

```text
open()  →  read()  →  close()
```

英文 `acquire` / `release` 在工程文档里很常见，所以课程会保留英文，但第一次出现时会同时给出中文含义。

### 5. 为什么需要 `finally`

如果资源必须关闭，仅仅把 `close()` 写在函数最后并不可靠：中途发生异常或提前 `return` 时，最后那一行可能根本执行不到。

```python
resource = open_resource()
try:
    use(resource)
finally:
    resource.close()
```

`finally` 的意思是：**无论 `try` 里面正常结束、提前返回，还是因为异常离开，这段收尾代码都应该执行。**

这里的 cleanup 就是“清理/收尾”，例如关闭文件、归还连接、释放锁。

### 6. `with` 和 context manager 是什么

**context manager（上下文管理器）** 是 Python 用来表达“进入一个使用范围，离开时自动收尾”的协议。

你其实很可能已经见过：

```python
with open("data.txt") as f:
    data = f.read()
```

可以按下面的方式理解：

```text
进入 with
  ↓
获得文件资源
  ↓
在缩进代码块中使用
  ↓
离开这个代码块
  ↓
文件被关闭
```

所以“把 acquire/use/release 放在同一个可见生命周期边界”这句话，用白话说就是：

> **从代码外观上就能看出：资源从哪里开始使用，到哪里一定结束。**

这里的“边界”就是 `with` 的缩进代码块。

本课练习使用标准库的 `@contextmanager` 帮助我们定义一个 context manager。你不需要研究装饰器内部实现，只要先记住它的结构：

```python
from contextlib import contextmanager

@contextmanager
def managed():
    # 进入 with 时执行
    resource = open_resource()
    try:
        yield resource  # 交给 `with ... as ...` 使用
    finally:
        # 离开 with 时执行
        resource.close()
```

这里的 `yield` 仍然有“暂停并把值交出去”的含义；只是 `@contextmanager` 利用了这个暂停点，把 `yield` 前后分别组织成“进入”和“退出”。

## 脑内执行模型

```text
进入 with
   │
   ├─ 获得资源
   │
   ├─ 需要一条 → 产生一条
   ├─ 需要一条 → 再产生一条
   │
   ├─ 调用者提前 break
   │
   └─ 离开 with → finally → 关闭资源
```

脑中要同时保存两件事：数据现在走到哪，以及资源什么时候一定会被关闭。

## 常见误解

- **误区：generator function 一调用就执行到第一个 `yield`。** 实际上调用时只创建 generator object，第一次 `next()` 才真正进入函数体。
- **误区：只有抛异常时 `finally` 才运行。** 正常结束、提前 `return` 或异常离开 `try` 时，都会进入 `finally`。
- **误区：`with` 只是“语法糖”，所以资源关闭并不重要。** “语法糖（syntactic sugar）”只是说“用更容易读的写法表达原本也能写出的逻辑”，不代表它表达的资源规则不重要。`with` 的价值正是让资源的开始和结束非常清楚。
- **误区：惰性处理就是执行得更快。** 它主要表示“不提前做没必要的工作/不提前把全部数据放进内存”，并不保证单条处理速度更快。

## 本节规则总结

1. iterable 表示“可以开始遍历”，iterator 表示“正在遍历并记得当前位置”。
2. `yield` 会产出一个值并暂停 generator；下一次从原位置继续。
3. “惰性”就是按需产生：需要一个才处理一个。
4. 必须执行的资源清理放进 `finally`，不要依赖调用者记得手工调用。
5. `with` 把资源的获得、使用和释放放在一个一眼可见的代码范围里。

## 关键问题

1. `batches()` 和 `next(batches_generator)` 分别在什么时候真正执行函数体？
2. `yield` 与 `return` 最大的执行流程区别是什么？
3. iterable 与 iterator 为什么不是同一个概念？
4. 如果只需要前 3 条记录，为什么“需要一条才读取一条”可能比先读完全部更合适？
5. 为什么 `finally` 比“在函数最后写 close()”更可靠？
6. `with` 的缩进代码块为什么可以看作一个资源生命周期边界？

## 场景命题

实现一个 `managed_records` 上下文管理器。

它接收一批输入记录，但**不要提前把全部记录复制或读取出来**；调用者需要下一条时，再逐条提供下一条记录。调用者可能只读前几条就停止，但离开 `with` 时资源必须关闭。

## 验收

测试会确认三件事：

1. 记录按照输入顺序逐条产生；
2. 实现不会为了开始遍历而提前把全部记录读完；
3. 无论正常结束还是调用者提前停止，离开 context 时都会执行一次资源清理。

仓库参考实现：

```bash
uv run pytest lessons/00_python_foundation/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/00_python_foundation/tests -v --learner
```
