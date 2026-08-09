# Lesson 09 — Blocking I/O

## 本节目标

学完本节，你应该能够：

- 判断同步调用是否会阻塞 Event Loop
- 使用 `asyncio.to_thread()` 桥接 blocking I/O
- 区分 I/O-bound 与 CPU-bound 工作
- 理解 thread-safe 为什么是复用旧同步库时的额外约束

## 进入本课前

你已经学过：Event Loop、Task、真实异步 I/O、并发上限和资源容量。

这一课新增 **blocking I/O、I/O-bound、CPU-bound、worker thread、thread-safe、legacy library**。

## 为什么需要学习它

真实项目里经常会遇到一个现实问题：

> 你正在写 asyncio 代码，但依赖的旧 SDK、文件库或数据库驱动只有同步 API。

如果这些同步调用会长时间等待，而你直接在 Event Loop 所在线程里调用它们，其他 Task 也会一起被卡住。

## 核心理论

### 1. blocking I/O 是什么

**blocking I/O（阻塞式 I/O）**指的是：

> 调用函数后，当前线程会一直停在这个函数里，直到外部 I/O 完成才返回。

例如：

```python
time.sleep(2)
requests.get(url)
```

如果在 Event Loop 线程里直接调用一个会等待 2 秒的同步函数，这 2 秒里 Event Loop 没机会调度别的 Task。

### 2. I/O-bound 与 CPU-bound

**I/O-bound（I/O 密集型）**：大部分时间在等待外部资源，例如网络、磁盘、数据库。

**CPU-bound（CPU 密集型）**：大部分时间在持续计算，例如大规模纯 Python 运算。

`to_thread()` 特别适合“同步 + 阻塞 I/O”这一类问题。

### 3. `asyncio.to_thread()` 做什么

```python
result = await asyncio.to_thread(blocking_sdk_call, arg)
```

它会把同步函数 `blocking_sdk_call(arg)` 放到另一个工作线程中执行。

**worker thread（工作线程）**就是专门拿来执行这些同步函数的线程。

当前 Task 仍然 `await` 它的结果，但 Event Loop 线程本身不再被这个同步调用占住，因此还能继续推进其他 Task。

```text
Event Loop thread: Task A 等结果 ──→ 继续调度 Task B / C
                         │
                         └── worker thread: blocking call ........
```

### 4. `to_thread()` 接收的是同步 callable

这里的 **callable（可调用对象）**就是“能像函数一样被调用的对象”。

`to_thread()` 的目标是把**同步函数**移到线程里，而不是把 coroutine 整体丢到线程里。

### 5. thread-safe 是什么

如果多个线程可能同时调用同一个对象，就要考虑它是否 **thread-safe（线程安全）**。

白话理解：

> 多个线程同时使用它时，它内部状态是否还能保持正确，不会互相踩坏。

有些旧 client 明确不允许被多个线程同时调用。这时即使使用 `to_thread()`，你也可能需要：

- 每个线程使用独立 client；或
- 用并发限制保证同一 client 不被同时调用。

### 6. legacy library 是什么

**legacy library（遗留库/旧库）**不是贬义，只表示：

> 已经存在并被业务使用，但设计时可能没有提供 asyncio 原生 API 的库。

工程中“桥接旧同步代码”往往比“全部重写成 async”更现实。

### 7. 为什么 CPU-bound 不应机械地 `to_thread()`

线程并不是所有 CPU 问题的万能解法。

纯 Python 重计算即使放到工作线程，也仍然会消耗大量 CPU，并且受到 Python 解释器线程执行模型的限制。

这一课只要求形成判断习惯：

```text
同步调用
  ↓
主要在等待 I/O？ → to_thread 往往合适
主要在持续计算？ → 不要直接套用同一方案，重新评估
```

## 脑内执行模型

```text
Event Loop thread: heartbeat ─ tick ─ tick ─ tick
                         │
                         └─ await to_thread(...)
worker thread:                [同步阻塞调用........]
```

## 常见误解

- **误区：同步函数代码很短，所以一定不会阻塞。** 函数体短不代表外部 I/O 最坏情况下很快。
- **误区：`to_thread()` 会把 coroutine 放到线程。** 它主要接收同步 callable。
- **误区：工作线程数量是无限的。** 线程池本身也有容量和排队。
- **误区：只要用了线程，就不用考虑下游并发限制。** 线程里的调用仍可能打爆外部资源。
- **误区：所有 CPU-bound 工作都应该 `to_thread()`。** CPU 问题需要单独评估。

## 本节规则总结

1. Event Loop 线程不能长时间执行阻塞同步调用。
2. blocking I/O 可以用 `asyncio.to_thread()` 桥接。
3. `to_thread()` 让同步调用在线程里运行，Event Loop 仍可继续调度其他 Task。
4. 旧同步 client 还要考虑 thread-safe。
5. I/O-bound 与 CPU-bound 要先分类，再选方案。

## 关键问题

1. 为什么在 coroutine 里直接调用 `time.sleep()` 会影响其他 Task？
2. `to_thread()` 把哪一部分工作移出了 Event Loop 线程？
3. I/O-bound 与 CPU-bound 的主要区别是什么？
4. thread-safe 是什么意思？为什么共享 legacy client 时必须考虑它？
5. 为什么线程池本身也需要容量意识？
6. 为什么 `to_thread()` 不是 CPU-bound 的通用答案？

## 场景命题

包装一个会 `time.sleep()` 的 legacy loader，批量加载多个 profile。

Event Loop 必须保持响应，同时限制工作线程中同时调用 loader 的数量。

## 验收

测试会运行一个 heartbeat（周期性执行的小任务）来确认 Event Loop 仍能继续推进，同时记录 legacy loader 在线程侧的峰值 active 数量。

仓库参考实现：

```bash
uv run pytest lessons/09_blocking_io/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/09_blocking_io/tests -v --learner
```
