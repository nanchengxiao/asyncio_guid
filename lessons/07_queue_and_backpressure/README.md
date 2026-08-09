# Lesson 07 — Queue and backpressure

## 本节目标

学完本节，你应该能够：

- 解释 backpressure 为什么必须向上游传播
- 使用 bounded Queue 连接 producer 与 consumers
- 设计 sentinel / shutdown
- 区分并发上限和 backlog 上限

## 为什么需要学习它

如果 producer 每秒产生 10 万条消息，而 consumer 每秒只能处理 1 万条，系统不可能靠“更多内存”永久解决。队列必须有边界，让上游在下游跟不上时感受到压力。

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

队列满时，`put()` 会等待。这不是性能故障，而是 backpressure 正在工作。`queue.join()` / `task_done()` 可以表达“已入队工作全部处理完成”。

这一阶段还会遇到两个常见 primitive：`Lock` 用来保护“多个 Task 跨 await 修改同一份共享状态”的临界区；`Event` 用来广播一个状态已经发生。它们都不是 Queue 的替代品：Queue 传递工作并承载 backlog，Lock 保护共享状态，Event 通知状态变化。

## 脑内执行模型

```text
producer: put put put [queue full......wait] put
consumer:       get --- work --- get --- work
                         时间 →
```

## 常见误解

- **误区：** Queue 越大吞吐越高。大队列通常只把过载延迟隐藏得更久。
- **误区：** 有 Semaphore 就不需要 Queue。Semaphore 控制 active；Queue 还控制等待 backlog。
- **误区：** producer 应先把所有输入读完再入队。这样背压无法传到最上游。
- **误区：** worker 取消就够了，不需要考虑已经入队的数据。shutdown 是否 drain 是业务决策。

## 本节规则总结

1. bounded Queue 是容量边界，也是反压信号。
2. producer 应直接 await put，让压力继续向源头传播。
3. consumer 完成一个 item 后调用 task_done。
4. shutdown 要明确 drain 还是 drop。
5. backlog 容量与 worker 并发是两个参数。

## 关键问题

1. Queue 满时 producer 的 await 表达了什么？
2. 为什么无限 Queue 容易把慢 downstream 变成内存问题？
3. Semaphore 和 bounded Queue 的边界分别在哪里？
4. 为什么必须把 backpressure 传到最上游读取逻辑？
5. graceful shutdown 时 sentinel、join、cancel 各自适合什么阶段？

## 场景命题

实现一个从 AsyncIterable 读取 job 的 producer/consumer pipeline。Queue 必须有 maxsize；worker 数固定；producer 不允许先把全部输入 materialize。

## 验收

测试使用可观测 AsyncIterable 检查 producer 的领先量有上界，并验证所有 job 恰好处理一次。

仓库参考实现：

```bash
uv run pytest lessons/07_queue_and_backpressure/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/07_queue_and_backpressure/tests -v --learner
```
