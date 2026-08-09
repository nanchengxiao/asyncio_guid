# Lesson 09 — Blocking I/O

## 本节目标

学完本节，你应该能够：

- 判断同步调用是否会阻塞 Event Loop
- 使用 `asyncio.to_thread()` 桥接 blocking I/O
- 区分 I/O-bound 与 CPU-bound
- 理解 thread-safe 为什么是旧同步库的额外约束

## 进入本课前

你已经学过 Event Loop、Task、真实异步 I/O 和并发上限。

本课新增：

- **blocking I/O（阻塞式 I/O）**：调用后，当前线程一直等到外部 I/O 完成才返回。
- **I/O-bound**：主要时间花在网络、磁盘、数据库等等待上。
- **CPU-bound**：主要时间花在持续计算上。
- **worker thread（工作线程）**：专门执行同步函数的另一条线程执行路径。
- **thread-safe（线程安全）**：多个线程同时使用同一对象时，它仍能保持内部状态正确。
- **legacy library（遗留/旧库）**：已经在业务中使用、但可能没有 asyncio 原生 API 的库。

## 为什么需要学习它

真实项目总会遇到没有 async API 的 SDK、文件库或数据库驱动。直接从 coroutine 调用会长时间等待的同步函数，会把 Event Loop 一起卡住。

## 核心理论

```python
result = await asyncio.to_thread(blocking_sdk_call, arg)
```

`to_thread()` 会让同步函数在线程中执行。当前 Task 等待结果时，Event Loop 线程仍能继续推进其他 Task。

```text
Event Loop thread: heartbeat ─ tick ─ tick ─ tick
                         │
                         └─ await to_thread(...)
worker thread:                [blocking call........]
```

`to_thread()` 接收的是同步 callable（能像函数一样被调用的对象），不是把 coroutine 整体丢到线程里。

如果多个线程可能同时调用同一个 legacy client，还要确认它是否 thread-safe；否则需要独立 client 或更严格的并发限制。

线程也不是 CPU-bound 的万能解法。纯 Python 重计算需要重新评估进程池或其他架构，不要机械套用 `to_thread()`。

## 脑内执行模型

```text
同步阻塞调用直接跑在 Event Loop 线程 → 其他 Task 也停住
同步阻塞调用放到 worker thread     → Event Loop 仍可调度其他 Task
```

## 常见误解

- **误区：** 同步函数代码很短，所以一定不会阻塞。关键看最坏情况下是否等待外部 I/O。
- **误区：** `to_thread()` 会把 coroutine 放到线程。它主要接收同步 callable。
- **误区：** 工作线程数量无限。线程池本身也有容量和排队。
- **误区：** 所有 CPU-bound 工作都应该 `to_thread()`。CPU 问题需要单独评估。

## 本节规则总结

1. Event Loop 线程不能长时间执行阻塞同步调用。
2. blocking I/O 可以用 `asyncio.to_thread()` 桥接。
3. 线程侧调用同样要考虑并发容量。
4. 共享 legacy client 时还要考虑 thread-safe。
5. I/O-bound 与 CPU-bound 要先分类，再选方案。

## 关键问题

1. 为什么在 coroutine 里直接调用 `time.sleep()` 会影响其他 Task？
2. `to_thread()` 把哪部分工作移出了 Event Loop 线程？
3. I/O-bound 与 CPU-bound 的区别是什么？
4. thread-safe 是什么意思？
5. 为什么 `to_thread()` 不是 CPU-bound 的通用答案？

## 场景命题

包装一个会 `time.sleep()` 的 legacy loader，批量加载多个 profile。Event Loop 必须保持响应，同时限制线程中同时调用 loader 的数量。

## 验收

测试会运行 heartbeat（周期性小任务）确认 Event Loop 仍能推进，并记录 loader 在线程侧的峰值 active 数量。

仓库参考实现：

```bash
uv run pytest lessons/09_blocking_io/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/09_blocking_io/tests -v --learner
```
