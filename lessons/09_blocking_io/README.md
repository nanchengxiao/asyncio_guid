# Lesson 09 — Blocking io

## 本节目标

学完本节，你应该能够：

- 判断同步调用是否会阻塞事件循环
- 使用 asyncio.to_thread 桥接 blocking I/O
- 理解线程桥接不等于 CPU 并行万能方案
- 给线程侧稀缺资源增加容量边界

## 为什么需要学习它

真实项目总会遇到没有 async API 的 SDK、文件库或数据库驱动。直接从协程调用阻塞函数会冻结事件循环上的所有 Task。

## 核心理论

```python
result = await asyncio.to_thread(blocking_sdk_call, arg)
```

`to_thread` 把同步 callable 放到工作线程，当前 Task 等待其结果时 event loop 可以继续推进其他 Task。它特别适合阻塞 I/O。纯 Python CPU-bound 工作通常需要重新评估进程池或其他架构，因为线程受解释器执行模型影响。

## 脑内执行模型

```text
event-loop thread: heartbeat ─ tick ─ tick ─ tick
                         │
                         └─ await to_thread(...)
worker thread:                [blocking SDK call........]
```

## 常见误解

- **误区：** 同步函数很短，所以一定不会阻塞。是否阻塞取决于最坏情况和外部 I/O。
- **误区：** to_thread 会把 coroutine 放到线程。它接收同步 callable。
- **误区：** 线程池是无限资源。默认线程池也有容量与排队，需要结合下游限制。
- **误区：** CPU-bound 代码都应该 to_thread。纯 Python 重计算未必获得多核收益，且仍消耗进程 CPU。

## 本节规则总结

1. 事件循环线程不能执行长时间阻塞调用。
2. blocking I/O 可以通过 to_thread 桥接。
3. 线程侧调用也要考虑 concurrency limit。
4. 线程安全是复用 legacy library 的额外约束。
5. CPU-bound 与 I/O-bound 要先分类。

## 关键问题

1. 直接调用 time.sleep/requests.get 为什么会冻结其他 Task？
2. to_thread 让哪一部分代码离开 event loop thread？
3. 如果 legacy client 不是线程安全的，设计要如何变化？
4. 为什么 to_thread 不是 CPU-bound 的通用答案？
5. 怎样用 heartbeat 测试证明事件循环没有被阻塞？

## 场景命题

包装一个会 `time.sleep()` 的 legacy loader，批量加载多个 profile。事件循环必须保持响应，同时限制线程中同时调用 loader 的数量。

## 验收

测试运行 heartbeat，并记录 legacy loader 的线程侧峰值 active。

仓库参考实现：

```bash
uv run pytest lessons/09_blocking_io/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/09_blocking_io/tests -v --learner
```
