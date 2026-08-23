# Practice — managed record stream

这一题不是让你“猜一个 API”，而是把 Lesson 00 的几个小概念组合起来。

如果下面任何一句看不懂，请先回到本课 README 对应小节：

- `iter(records)`：从“可以开始遍历的数据”得到“记住当前遍历位置的 iterator”
- 按需读取（lazy，常译为“惰性”）：需要一条才读取一条，不提前把后面的数据读完
- callback：把一个函数作为参数传进来，稍后再调用
- `try/finally`：无论怎样离开，都执行必须做的收尾
- `@contextmanager`：用一次 `yield` 表达 context 的进入/退出分界

## 业务背景

报表导入器从一个必须显式关闭的数据源逐条读取记录。

调用方可能：

1. 把所有记录都读完；
2. 只读第一条就结束；
3. 在 `with` 代码块中途抛异常。

无论哪种情况，只要离开 `with`，底层资源都必须关闭一次。

## 你要实现的接口

```python
with managed_records(records, close_resource) as stream:
    first = next(stream)
```

参数：

- `records`：一份“可以开始遍历的数据”；它可能是 list，也可能是 generator
- `close_resource`：一个不接收参数的函数；调用它表示释放资源

`as stream` 应该得到：

- 一个 iterator
- 可以用 `next(stream)` 一步步读取
- 不应该在进入 context 时就把所有数据读完

这里的 `stream`（流）不是某个特殊 Python 类型，只表示“可以一条一条取得记录的数据来源”。

## 先手工拆成 3 个问题

### 问题 1：怎样做到“需要一条才读取一条”？

你需要的是 iterator：

```python
iterator = iter(records)
```

不要这样做：

```python
all_records = list(records)
```

因为 `list(...)` 会把输入一次性消费完。

### 问题 2：谁保证资源一定关闭？

不是调用方的 `break`。

本题的明确生命周期边界是：

```python
with managed_records(...) as stream:
    ...
```

所以资源关闭应该和这个 context 的退出绑定。

### 问题 3：`@contextmanager` 应该把什么交给 `as stream`？

`@contextmanager` 函数里的那一次 `yield`，它的值会交给 `as` 后面的变量。

这里应该交出“可以被调用方逐步 `next()` 的对象”。

## 推荐实现顺序

不要一次写完。按下面顺序做：

1. 先得到 `iterator = iter(records)`。
2. 用 `try/finally` 建立收尾边界。
3. 在 `try` 中通过 `yield` 把 iterator 交给调用方。
4. 在 `finally` 中调用 `close_resource()`。
5. 跑测试，观察哪条行为还不满足。

Starter 已经给了结构提示，你只需要填两个 TODO。

## 约束

- 不得把输入一次性转成 list。
- 不要主动把所有 records 预读完。
- 无论正常退出、提前停止还是 `with` body 抛异常，退出 context 时都调用 cleanup。
- cleanup 恰好一次。

## 先做一个人工预测

假设：

```python
events = []


def source():
    for item in [1, 2, 3]:
        events.append(f"produce:{item}")
        yield item
```

然后：

```python
with managed_records(source(), lambda: events.append("closed")) as stream:
    first = next(stream)
```

正确结果应该是：

```python
first == 1
events == ["produce:1", "closed"]
```

不应该出现：

```python
["produce:1", "produce:2", "produce:3", "closed"]
```

否则说明你提前消费了整个输入，不符合“需要一条才读取一条”。

## 验收

运行学习者版本：

```bash
uv run pytest lessons/00_python_foundation/tests -v --learner
```

如果失败，先看失败行为属于哪一类：

- `next(stream)` 失败：检查你 `yield` 给调用方的对象是什么；
- 一进入 `with` 就产生全部数据：检查是否用了 `list(...)` 或提前遍历；
- 没有 `closed`：检查 cleanup 是否在 `finally`；
- 异常路径没 cleanup：检查 `finally` 是否真正包住了 `yield` 生命周期；
- 出现两个 `closed`：检查你是否在多个地方重复调用 cleanup。

测试通过后再打开：

```text
../solution/reference.py
```

并尝试不用看代码回答：

1. 为什么需要 `iter(records)`？
2. 为什么 `yield` 的是 iterator，而不是 `next(iterator)`？
3. 为什么 `close_resource()` 放在 `finally`？
4. 为什么调用方提前停止本身不是 cleanup 保证？
