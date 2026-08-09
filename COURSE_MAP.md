# Course Map

## Stage 0 — Python 必要基础

### Lesson 00：Python foundation
**一句话目标：** 用 generator / context manager / `finally` 建立“暂停、恢复、资源生命周期”的前置模型。  
**实践：** 实现一个流式记录读取器，消费提前结束时也必须关闭资源。  
**验收：** 数据顺序正确；提前退出仍执行 cleanup。

## Stage 1 — Coroutine / await

### Lesson 01：Coroutine and await
**一句话目标：** 看到 `foo()`、`await foo()` 时能判断 coroutine 何时真正开始执行。  
**实践：** 构建订单上下文，保持真实数据依赖，不制造虚假并发。  
**验收：** 调用顺序符合依赖；仅创建 coroutine object 不执行函数体。

## Stage 2 — Event Loop / Task / 并发

### Lesson 02：Event loop and Task
**一句话目标：** 理解并发来自多个同时存活的 Task，而不是 `await` 本身。  
**实践：** 并发获取 dashboard 的 user 与 orders。  
**验收：** 正确性 + 受控延迟下显著快于串行基线。

## Stage 3 — Task 生命周期与 Structured Concurrency

### Lesson 03：Structured concurrency
**一句话目标：** 对每个 Task 都能回答“谁拥有、谁等待、谁取消、谁处理异常”。  
**实践：** 用一个父作用域管理兄弟任务，并在其中一个失败时取消其余任务。  
**验收：** 失败传播；sibling 收到取消；cleanup 执行；无 orphan task。

## Stage 4 — Timeout / Cancellation / Exception

### Lesson 04：Cancellation
**一句话目标：** 把 cancellation 当作正常控制流，并用 `finally` 保证清理。  
**实践：** 可取消的分片上传。  
**验收：** `cancel()` 后清理发生且 `CancelledError` 继续传播。

### Lesson 05：Timeout and errors
**一句话目标：** 为异步业务调用显式设计 success / exception / timeout / cancellation 四种结果。  
**实践：** 调用多个 required/optional 下游，并分类 TaskGroup 的并行失败。  
**验收：** timeout 生效；required 失败传播；`ExceptionGroup` 可分类。

## Stage 5 — Semaphore / Queue / Backpressure

### Lesson 06：Bounded concurrency
**一句话目标：** 区分“任务数量”和“资源允许同时访问的数量”。  
**实践：** 大批请求通过有限容量的下游资源。  
**验收：** 全部结果正确；峰值 active 从不超过 limit；仍保留并发。

### Lesson 07：Queue and backpressure
**一句话目标：** 让下游处理不过来的压力通过 bounded Queue 自然传回 producer。  
**实践：** producer → bounded queue → consumers 流水线。  
**验收：** 无丢失；producer 不能无限领先；worker 可干净退出。

## Stage 6 — 真实 I/O 与同步桥接

### Lesson 08：Real async I/O
**一句话目标：** 把 HTTP 连接池视为真实资源容量，而不是把网络调用当成 `sleep()`。  
**实践：** 使用 aiohttp 访问本地测试服务器并限制连接池。  
**验收：** 不依赖公网；响应正确；服务器观测到的峰值并发受连接池限制。

### Lesson 09：Blocking I/O
**一句话目标：** 判断阻塞同步 I/O 何时会卡住事件循环，并用 `asyncio.to_thread()` 桥接。  
**实践：** 包装同步 legacy SDK。  
**验收：** heartbeat 在阻塞调用期间仍推进；线程侧并发受控。

## Stage 7 — 业务异步建模

### Lesson 10：Business modeling
**一句话目标：** 先回答六问、画 DAG，再决定 Task 与并发结构。  
**实践：** Async Service Aggregator。  
**验收：** 第一层依赖并发；第二层按 DAG 启动；optional failure 被隔离；required failure 传播。

## Stage 8 — 生产级 asyncio

### Lesson 11：Production asyncio
**一句话目标：** 把生命周期、资源容量、速率、失败恢复与可观测性组合成一个可解释的服务。  
**实践：** Job Processing Service。  
**验收：** bounded queue、API concurrency、rate limit、timeout、有限 retry、idempotency、有限 writer 容量、graceful drain、metrics/logging。
