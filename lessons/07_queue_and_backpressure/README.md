# Lesson 07 — Queue and backpressure

## 本节目标

学完本节，你应该能够：

- 使用 bounded Queue 连接 producer 与 consumer
- 解释 backpressure 为什么要向上游传播
- 区分并发上限与 backlog 上限
- 让 worker 在工作结束后干净退出

## 进入本课前

你已经学过 active concurrency、backlog 和 Semaphore。

本课新增：

- **producer（生产者）**：负责产生待处理工作。
- **consumer（消费者）**：从 Queue 取工作并处理。
- **bounded Queue**：有 `maxsize` 上限的队列，用来限制等待中的 backlog。
- **backpressure（反压）**：下游处理不过来时，让上游也慢下来，而不是无限堆积。
- **AsyncIterable**：可以用 `async for` 逐项异步读取的数据源；取下一项本身可能需要等待。
- **sentinel（结束标记）**：放进 Queue 的特殊值，用来告诉 worker“没有新工作了”。
- **drain（排空）**：停止接收新工作，但把已经接收的工作处理完。

## 为什么需要学习它

如果 producer 每秒产生 10 万条消息，而 consumer 每秒只能处理 1 万条，系统不可能靠“更多内存”永久解决。Queue 必须有边界，让上游在下游跟不上时感受到压力。

## 核心理论

```text
Producer
   │ await queue.put(item)
   ▼
bounded Queue (maxsize=N)
   │
   ├─ Consumer 1
   ├─ Consumer 2
   └─ Consumer 3
```

Queue 满时，`await queue.put(item)` 会等待。这不是故障，而是 backpressure 正在工作：consumer 处理不过来，producer 就不能继续无限领先。

Semaphore 与 Queue 的边界不同：

```text
Semaphore / worker 数量 → 限制 active concurrency
Queue maxsize           → 限制等待中的 backlog
```

producer 不应该先把 AsyncIterable 全部读完再入队，否则压力已经提前变成内存占用，Queue 无法把 backpressure 传回真正的数据源。

consumer 处理完一个 item 后调用：

```python
queue.task_done()
```

另一边可以用：

```python
await queue.join()
```

等待所有已入队工作都真正处理完成。`get()` 只是“取走”，`task_done()` 才表示“处理完成”。

## 脑内执行模型

```text
producer: put put put [queue full......wait] put
consumer:       get ─ work ─ done ─ get ─ work
                         时间 →
```

## 常见误解

- **误区：** Queue 越大吞吐越高。大 Queue 往往只是把过载隐藏得更久。
- **误区：** 有 Semaphore 就不需要 Queue。Semaphore 控制 active，Queue 还能控制 backlog。
- **误区：** producer 可以先把所有输入读完。这样 backpressure 无法传回上游。
- **误区：** `queue.get()` 后就算处理完成。处理完成后仍应调用 `task_done()`。

## 本节规则总结

1. producer 产生工作，consumer 处理工作，Queue 在它们之间传递工作。
2. bounded Queue 限制 backlog。
3. Queue 满时 producer 等待，就是 backpressure。
4. producer 应逐项读取 source，不要提前 materialize（把全部内容一次性读入内存）。
5. shutdown 时要明确 drain 还是直接丢弃剩余工作。

## 关键问题

1. producer、Queue、consumer 各负责什么？
2. `maxsize` 限制的是 active concurrency 还是 backlog？
3. 为什么 Queue 满时让 `put()` 等待是合理行为？
4. 为什么不能先把 AsyncIterable 全部读完再入队？
5. `get()`、`task_done()`、`join()` 分别表达什么？
6. sentinel 和 drain 各解决什么问题？

## 场景命题

实现 producer → bounded Queue → 固定数量 worker 的流水线。source 很快时必须被 Queue 反压，不能提前把所有 job 读进内存。

## 验收

测试会确认所有 job 恰好处理一次、producer 的领先量有上界，并且 worker 能干净退出。

仓库参考实现：

```bash
uv run pytest lessons/07_queue_and_backpressure/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/07_queue_and_backpressure/tests -v --learner
```
