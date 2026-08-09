# Lesson 07 — Queue and backpressure

## 本节目标

学完本节，你应该能够：

- 解释 Queue 为什么能把“生产工作”和“处理工作”连接起来
- 理解 bounded Queue 如何限制 backlog
- 解释 backpressure（反压）为什么必须向上游传播
- 理解 producer / consumer、`task_done()` / `join()` 的基本职责
- 设计一个能够干净结束的 worker 流水线

## 进入本课前

你已经学过：Task、bounded concurrency、Semaphore、active concurrency 和 backlog。

这一课新增 **Queue、producer/consumer、bounded Queue、backpressure、AsyncIterable、sentinel、drain**。

## 为什么需要学习它

上一课解决的是：

> 同一时间最多允许多少个工作真正占用资源？

但还有另一个问题：

> 如果新工作产生得比处理速度快，那些“还没轮到处理”的工作放在哪里？最多允许堆多少？

这就是 Queue 与 backpressure 要解决的问题。

## 核心理论

### 1. producer 和 consumer 是什么

**producer（生产者）**：负责产生待处理工作。

**consumer（消费者）**：负责从队列中取出工作并处理。

```text
Producer
   ↓
 Queue
   ↓
Consumers
```

例如：

```text
读取文件中的 job → Queue → 3 个 worker 调 API
```

### 2. Queue 是什么

`asyncio.Queue` 是 Task 之间传递工作的容器。

producer：

```python
await queue.put(item)
```

consumer：

```python
item = await queue.get()
```

如果暂时没有 item，consumer 可以等待；如果使用有容量上限的 Queue，队列满时 producer 也可以等待。

### 3. bounded Queue 是什么

```python
queue = asyncio.Queue(maxsize=10)
```

这表示队列中最多积压 10 个尚未取走的 item。

这和 Semaphore 的边界不同：

```text
Queue maxsize → 限制“等待处理的 backlog”
worker / Semaphore → 限制“正在处理的 active 工作”
```

### 4. backpressure 是什么

**backpressure（反压）**可以用一句白话理解：

> 下游处理不过来时，不是无限堆积，而是让上游也慢下来。

假设 consumer 很慢，Queue 已经满了：

```python
await queue.put(item)
```

producer 会停在这里等待空位。

这不是 bug，而是在告诉上游：

> “后面已经塞满了，先别继续生产这么快。”

如果 producer 自己又是从网络、文件或其他数据源读取，那么它被 `queue.put()` 卡住以后，就会自然减少继续读取的速度。这样压力才能一路传回源头。

### 5. 为什么不能先把所有输入读完

错误思路：

```python
all_items = [item async for item in source]
for item in all_items:
    await queue.put(item)
```

这已经把全部输入放进内存，Queue 的容量限制失去了意义。

正确思路是：

```text
从 source 取一个
↓
put 一个
↓
如果 Queue 满，就等
↓
有空位后再继续从 source 取
```

### 6. AsyncIterable 是什么

本课练习里的 `source` 是 **AsyncIterable（异步可迭代对象）**。

它和 Lesson 00 的 iterable 很像，区别是：取得“下一项”的过程本身可能需要异步等待，因此使用：

```python
async for item in source:
    ...
```

你现在只需要把它理解为：

> “可以逐项异步读取的数据源。”

不需要在这一课研究 `__aiter__` / `__anext__` 的底层协议。

### 7. `task_done()` 和 `join()` 是什么

consumer 从 Queue `get()` 一个 item 后，处理完成时调用：

```python
queue.task_done()
```

它的意思是：“刚才取走的那一项，现在真的处理完了。”

另一边可以：

```python
await queue.join()
```

等待“所有已经放进 Queue 的工作都被标记为完成”。

注意：`get()` 只表示拿走了，`task_done()` 才表示处理完了。

### 8. sentinel 和 drain

worker 常常是循环等待下一项：

```python
while True:
    item = await queue.get()
```

业务工作全部结束后，需要告诉 worker“没有下一项了”。一个常见办法是放入一个特殊值作为结束信号，这个值叫 **sentinel（哨兵值/结束标记）**。

**drain（排空）**则表示：

> 停止接收新工作，但把已经接收的工作继续处理完。

Lesson 11 会把 drain 放到 graceful shutdown 中进一步讨论。

## 脑内执行模型

```text
producer: put put put [Queue 满......等待] put
consumer:       get ─ work ─ task_done ─ get ─ work
                         时间 →
```

## 常见误解

- **误区：Queue 越大，吞吐一定越高。** 大 Queue 很多时候只是让积压更晚暴露，并增加内存与等待时间。
- **误区：有 Semaphore 就不需要 Queue。** Semaphore 控制 active concurrency，Queue 还能限制 backlog。
- **误区：producer 可以先把所有输入读取完。** 这样 backpressure 无法传回真正的数据源。
- **误区：`queue.get()` 以后就算处理完成。** 处理结束后还要调用 `task_done()`，`join()` 才能知道整批工作已经完成。

## 本节规则总结

1. producer 产生工作，consumer 处理工作，Queue 负责在它们之间传递工作。
2. bounded Queue 限制等待中的 backlog。
3. Queue 满时 producer 等待，就是 backpressure 正在生效。
4. producer 不应提前把全部 source 读进内存。
5. `task_done()` 表示一项真正处理完；`join()` 等待所有已入队工作完成。
6. worker 的结束方式要明确设计，例如使用 sentinel。

## 关键问题

1. producer、Queue、consumer 各负责什么？
2. Queue `maxsize=10` 限制的是 active concurrency 还是 backlog？
3. 为什么 Queue 满时让 `put()` 等待是一件好事？
4. 为什么 producer 不能先把 AsyncIterable 全部读完再入队？
5. `get()`、`task_done()`、`join()` 各表达什么状态？
6. sentinel 是用来解决什么问题的？
7. drain 与“直接丢掉队列里剩余工作”有什么业务差异？

## 场景命题

实现一个流水线：从一个 AsyncIterable 数据源逐项读取 job，通过有 `maxsize` 的 Queue 交给固定数量的 worker 处理。

如果 source 很快而 worker 很慢，producer 必须在 Queue 满时停下来，不能提前把所有 job 都读取进内存。

## 验收

测试会确认：

- 所有 job 都恰好处理一次；
- producer 最多只能领先一个受 Queue 容量限制的数量；
- worker 能在工作结束后干净退出。

仓库参考实现：

```bash
uv run pytest lessons/07_queue_and_backpressure/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/07_queue_and_backpressure/tests -v --learner
```
