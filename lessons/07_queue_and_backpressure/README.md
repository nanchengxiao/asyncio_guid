# Lesson 07 — 让等待中的工作也有明确上限

## 进入本课前

你已经学过 active concurrency、backlog、Semaphore、worker、downstream 和 rate limit。

## 本课新增术语

- **Queue（队列）**：在多份 async 工作之间临时存放待处理 item 的容器；一边放进去，另一边取出来处理。
- **producer（生产者）**：负责产生待处理 item，并把它们放进 Queue 的代码。
- **consumer（消费者）**：从 Queue 取出 item 并处理的代码；本课的 worker 就是 consumer。
- **upstream（上游）**：更早产生数据或工作的那一侧；本课中 producer 和它读取的数据源都属于 upstream。
- **`maxsize`**：Queue 允许同时存放多少个等待中 item 的容量上限。
- **bounded Queue（有容量上限的队列）**：设置了 `maxsize`，因此等待中的 item 数量不能无限增长的 Queue。
- **backpressure（反压）**：downstream 处理不过来时，让 upstream 也慢下来，而不是继续无限堆积等待工作。
- **`queue.put(item)`**：把一个 item 放进 Queue；bounded Queue 已满时，这一步会等待。
- **`queue.get()`**：从 Queue 取出一个 item；Queue 为空时，这一步会等待。
- **`queue.task_done()`**：告诉 Queue“刚才取出的一个 item 已经真正处理完成”。
- **`queue.join()`**：等待所有已经放进 Queue 的 item 都被标记为处理完成。
- **AsyncIterable（异步可迭代对象）**：一种逐项取得数据时允许等待的数据源；请求下一项不一定能立刻拿到结果。
- **`async for`**：逐项读取 AsyncIterable 的 Python 语法；每次取得下一项时都允许 async 等待。
- **sentinel（结束标记）**：放进 Queue 的一个特殊值，用来告诉 consumer“已经没有新工作了”。
- **drain（排空）**：停止接收新的工作，但把已经接收的工作继续处理完。
- **pipeline（流水线）**：把多个处理环节串起来，让数据从上一环节流向下一环节的结构。

## 本节目标

学完本节，你应该能够：

- 使用 bounded Queue 连接 producer 与 consumer；
- 解释 backpressure 为什么需要传回 upstream；
- 区分 active concurrency 上限与 backlog 上限；
- 使用 `task_done()` / `join()` 表达“已处理完成”；
- 使用 sentinel 或明确结束规则让 worker 干净退出；
- 解释 drain 与“立刻丢弃剩余工作”的区别。

## 为什么需要学习它

前一课用 `Semaphore` 限制了 active concurrency，但还有一个问题没有解决：

> 如果 producer 很快，等待中的工作会不会一直增加？

假设 producer 每秒产生 10 万条 item，而 consumer 每秒只能处理 1 万条。只要这个速度差长期存在，backlog 就会不断变大。

程序不能靠“多给一点内存”永久解决这个问题。必须让等待区有上限，并在 downstream 跟不上时让 upstream 感受到压力。

## 核心理论

### 1. Queue 把 producer 与 consumer 分开

```text
producer
   │ await queue.put(item)
   ▼
Queue
   │
   ├─ consumer 1
   ├─ consumer 2
   └─ consumer 3
```

Producer 只负责产生 item；consumer 只负责处理 item；Queue 负责在两者之间保存尚未处理的内容。

### 2. `maxsize` 给 backlog 建边界

```python
queue = asyncio.Queue(maxsize=10)
```

这里表示：Queue 最多只允许 10 个 item 在里面等待。

当 Queue 已经满时：

```python
await queue.put(item)
```

会等待，而不是无限继续塞入。

这正是 backpressure：

```text
consumer 处理不过来
        ↓
Queue 变满
        ↓
producer 的 put() 开始等待
        ↓
producer 也被迫慢下来
```

### 3. Semaphore 与 Queue 控制不同边界

```text
Semaphore / worker 数量 → 控制 active concurrency
Queue maxsize           → 控制 backlog
```

两者经常需要一起使用。

只用 Queue，可能仍有太多 consumer 同时访问 downstream；只用 Semaphore，又可能有大量工作在其他地方排队。

### 4. 不要先把数据源全部读完

假设 source 是 AsyncIterable：

```python
async for item in source:
    await queue.put(item)
```

这样 producer 每取得一个 item，就尝试放进 Queue。Queue 满后，`put()` 会等待，于是 producer 暂时不会继续读取 source。

这才能把 backpressure 一直传回真正的数据源。

不要先做类似：

```python
items = [item async for item in source]
```

再慢慢入队。这样等于先把全部内容一次性读入内存，Queue 已经来不及限制 upstream 读取。

### 5. `get()` 只表示“取走”，不表示“处理完成”

Consumer 常见结构：

```python
item = await queue.get()
try:
    await handle(item)
finally:
    queue.task_done()
```

`get()` 把 item 从 Queue 取出来；真正处理完成后，再调用 `task_done()`。

另一边可以：

```python
await queue.join()
```

等待所有已经放进 Queue 的 item 都对应完成一次 `task_done()`。

### 6. Sentinel 用来告诉 worker“没有新工作了”

如果有固定数量 worker，可以在 producer 结束后放入结束标记：

```text
普通 item
普通 item
SENTINEL
SENTINEL
```

每个 worker 读到 sentinel 后结束自己的循环。

Sentinel 不是 asyncio 特殊对象；它只是双方约定的特殊值。

### 7. Drain 表达一种停止承诺

停止 pipeline 时有两种很不同的业务策略：

```text
策略 A：立刻停止，剩余工作可以丢弃
策略 B：停止接收新工作，但已经接收的必须处理完
```

策略 B 就是 drain。

本课只先建立这个词；最后一课会把 drain 放进完整程序的停止流程中。

## 脑内执行模型

```text
producer: put put put [Queue 已满……等待] put
consumer:       get ─ 处理 ─ 完成 ─ get ─ 处理
                         时间 →
```

当 consumer 变慢：

```text
consumer 慢
   ↓
Queue 中等待的 item 数量上升
   ↓
达到 maxsize
   ↓
producer await put()
   ↓
source 暂时不再继续读
```

## 常见误解

- **误区：** Queue 越大，程序一定处理得越快。  
  **更准确：** 更大的 Queue 往往只是允许更多 backlog 在内存里等待。

- **误区：** 有 Semaphore 就不需要 Queue。  
  **更准确：** Semaphore 控制 active concurrency；Queue 还能控制 backlog。

- **误区：** producer 可以先把所有输入读完。  
  **更准确：** 这样 backpressure 无法传回真正的数据源。

- **误区：** `queue.get()` 后就算处理完成。  
  **更准确：** 真正完成后还应调用 `task_done()`。

- **误区：** Sentinel 会自动结束所有 worker。  
  **更准确：** 它只是一个约定值，worker 必须自己识别并结束。

- **误区：** drain 就是立即停止。  
  **更准确：** drain 的承诺恰恰是把已经接收的工作处理完。

## 本节规则总结

1. Producer 产生 item，consumer 处理 item，Queue 在中间传递。
2. `maxsize` 是 Queue 的 backlog 容量上限。
3. Queue 满时 producer 的 `put()` 等待，就是 backpressure 正在工作。
4. Producer 应逐项读取 AsyncIterable，不要提前把全部内容读入内存。
5. `get()` 表示取走；`task_done()` 表示处理完成；`join()` 等待所有已入队 item 完成。
6. Sentinel 可以表达“没有新工作了”。
7. Drain 表达“停止接收新工作，但处理完已接收工作”。

## 关键问题

1. Queue 在 producer 与 consumer 之间负责什么？
2. upstream 与 downstream 分别是哪一侧？
3. bounded Queue 的 `maxsize` 限制的是 active concurrency 还是 backlog？
4. backpressure 用白话怎样解释？
5. 为什么 Queue 满时让 `put()` 等待是合理行为？
6. AsyncIterable 与普通 iterable 的关键差别是什么？
7. `async for` 为什么适合逐项读取 AsyncIterable？
8. 为什么不能先把 AsyncIterable 全部读完再入队？
9. `get()`、`task_done()`、`join()` 分别表达什么？
10. sentinel 解决什么问题？
11. drain 与立即丢弃剩余工作有什么区别？
12. pipeline 在本课里是什么意思？

## 场景命题

实现一个 producer → bounded Queue → 固定数量 worker 的 pipeline。

数据源很快时，producer 必须被 Queue 的 backpressure 限制，不能提前把所有 job 读进内存。

## 验收

测试会确认：

- 所有 job 恰好处理一次；
- producer 的领先量有明确上界；
- Queue 满时 producer 确实等待；
- worker 能在没有新工作后干净退出；
- 没有通过“先把全部数据源读进内存”绕过 backpressure。

仓库参考实现：

```bash
uv run pytest lessons/07_queue_and_backpressure/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/07_queue_and_backpressure/tests -v --learner
```
