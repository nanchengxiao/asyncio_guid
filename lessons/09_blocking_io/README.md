# Lesson 09 — 让会长时间等待的普通函数不要拖住其他工作

## 进入本课前

你已经学过 Event Loop、Task、thread、真实 async I/O 和 bounded concurrency。

## 本课新增术语

- **synchronous call（同步调用）**：像普通 Python 函数调用一样，当前执行路径会一直跑到这个调用返回，期间不会自动让别的 async 工作得到执行机会。
- **blocking I/O（阻塞式 I/O）**：synchronous call 在等待外部 I/O 时，当前 thread 仍被这个调用占住。
- **I/O-bound（I/O 密集型）**：总时间主要花在等待外部 I/O，而不是持续做计算。
- **CPU（处理器）**：真正执行程序计算指令的硬件；本课只需要把它理解成“负责算东西的地方”。
- **CPU-bound（计算密集型）**：总时间主要花在 CPU 持续执行计算，而不是等待外部 I/O。
- **worker thread（工作线程）**：专门替 Event Loop thread 执行普通同步函数的另一条 thread。
- **thread pool（线程池）**：管理一组 worker thread 的容器；提交的同步工作会在线程可用时执行。
- **`asyncio.to_thread()`**：把一个普通同步函数交给 worker thread 执行，并让当前 Task 以 async 方式等待其结果的工具。
- **thread-safe（线程安全）**：同一个对象被多个 thread 同时使用时，内部状态仍能保持正确。
- **API（接口）**：一个程序或库明确提供给其他代码调用的一组能力。
- **SDK（软件开发工具包）**：为了调用某个外部系统而提供的一组库、对象和 API。
- **legacy library（遗留/旧库）**：业务已经在使用、但设计时可能没有提供 asyncio API 的库。
- **client object（客户端对象）**：代码里代表某个外部系统调用入口的对象，例如旧 SDK 创建出来的 client。
- **heartbeat（心跳任务）**：周期性执行很小工作，用来观察 Event Loop 是否还能持续调度其他 Task。

## 本节目标

学完本节，你应该能够：

- 判断 synchronous call 是否会 blocking Event Loop thread；
- 使用 `asyncio.to_thread()` 桥接 blocking I/O；
- 区分 I/O-bound 与 CPU-bound；
- 解释 worker thread 与 thread pool 的作用；
- 理解 thread-safe 为什么会成为 legacy SDK 的额外约束；
- 用 heartbeat 验证 Event Loop 是否仍能持续推进。

## 为什么需要学习它

真实项目经常会遇到没有 asyncio API 的旧 SDK、文件库或其他数据访问库。

这些库可能只能提供普通同步函数。如果 coroutine 直接调用一个会长时间等待的同步函数，这个函数会一直占住 Event Loop thread，于是其他 Task 也得不到 scheduling 机会。

问题不在于“函数是不是 `def`”，而在于：

> 它最坏情况下会不会长时间占住 Event Loop thread？

## 核心理论

### 1. 直接调用 blocking I/O 会拖住 Event Loop

```python
async def load_profile():
    profile = legacy_loader()
    return profile
```

如果 `legacy_loader()` 内部执行类似：

```python
time.sleep(1)
```

那么这 1 秒里，当前 Event Loop thread 被 synchronous call 占住。

其他 Task 即使已经可以继续，也没有机会运行。

脑内模型：

```text
Event Loop thread:
Task A → legacy_loader() [等待.................] → return
Task B →                       无法推进
Task C →                       无法推进
```

### 2. `to_thread()` 把同步函数移到 worker thread

```python
result = await asyncio.to_thread(blocking_sdk_call, arg)
```

这行代码做两件事：

1. 把 `blocking_sdk_call(arg)` 交给 worker thread 执行；
2. 当前 Task async 等待它的结果，所以 Event Loop thread 可以继续 scheduling 其他 Task。

```text
Event Loop thread: heartbeat ─ tick ─ tick ─ tick
                         │
                         └─ await to_thread(...)
worker thread:                [blocking call........]
```

### 3. `to_thread()` 接收普通同步函数

```python
result = await asyncio.to_thread(load_sync, item)
```

这里 `load_sync` 是普通同步函数。

不要把 `to_thread()` 理解成“把整个 coroutine 搬到 thread 里”。Coroutine 仍然由 Event Loop 管理；只是其中那段同步阻塞工作被交给 worker thread。

### 4. Thread pool 自己也有容量

`to_thread()` 背后需要可用 worker thread。

如果同时提交大量同步调用，它们不会凭空获得无限 thread，而是可能在线程池里排队。

所以线程侧也有 resource 模型：

```text
很多同步调用
    ↓
容量有限的 thread pool
    ↓
少量 worker thread 同时执行
```

这和前面学过的 bounded concurrency 思路一致：

> 任何有限执行 resource，都应该考虑容量与等待位置。

### 5. 共享 client object 时要确认 thread-safe

假设旧 SDK 提供：

```python
client = LegacyClient()
```

然后多个 worker thread 同时调用：

```python
client.load(...)
```

这时要问：这个 `client` 是否 thread-safe？

如果文档明确说“不是 thread-safe”，就不能让多个 thread 同时共享使用同一个对象。

可能的处理方式包括：

- 每个 thread 使用独立 client object；
- 把同时调用数量限制为 1；
- 使用库官方建议的 thread 使用方式。

具体方案取决于旧库自己的保证。

### 6. I/O-bound 与 CPU-bound 先分类

`to_thread()` 主要解决的是：

> 普通同步函数因为等待 I/O 而长时间占住 Event Loop thread。

这属于 I/O-bound 问题。

如果函数一直做大量纯 Python 计算：

```python
for ...:
    heavy_calculation()
```

那是 CPU-bound 问题。

本课不展开 CPU-bound 的完整解决方案，只建立规则：

> 不要因为 `to_thread()` 能包装同步函数，就把所有重计算都机械丢进去。

先判断时间到底花在“等待外部结果”还是“持续计算”。

### 7. Heartbeat 可以观察 Event Loop 是否被拖住

定义一个很小的 heartbeat：

```python
async def heartbeat(events):
    for _ in range(3):
        events.append("tick")
        await asyncio.sleep(0.01)
```

如果另一个 Task 同时执行长时间 blocking I/O，而且 heartbeat 很久都不产生 `tick`，说明 Event Loop thread 被占住了。

如果 blocking I/O 正确放进 worker thread，heartbeat 应该仍能持续推进。

## 脑内执行模型

直接调用普通阻塞函数：

```text
Event Loop thread
   ↓
blocking synchronous call
   ↓
等待外部 I/O
   ↓
其他 Task 也无法推进
```

使用 `to_thread()`：

```text
Event Loop thread ─ await result ──→ 继续 scheduling 其他 Task
        │
        └─ 把同步函数交给 worker thread
                         ↓
                   blocking I/O
```

## 常见误解

- **误区：** 同步函数代码很短，所以一定不会 blocking。  
  **更准确：** 关键看它最坏情况下是否长时间等待外部 I/O。

- **误区：** `to_thread()` 会把 coroutine 搬到 thread。  
  **更准确：** 它主要执行普通同步函数；当前 coroutine 只负责 async 等待结果。

- **误区：** worker thread 数量无限。  
  **更准确：** thread pool 自己也有容量和排队。

- **误区：** 同一个 legacy client 可以默认被多个 thread 同时使用。  
  **更准确：** 要先确认它是否 thread-safe。

- **误区：** 所有 CPU-bound 工作都应该 `to_thread()`。  
  **更准确：** CPU-bound 需要单独评估，本课不把 `to_thread()` 当万能方案。

## 本节规则总结

1. Synchronous call 会一直占住当前执行路径直到返回。
2. Blocking I/O 直接跑在 Event Loop thread 上，会拖住其他 Task。
3. `asyncio.to_thread()` 可以把普通同步函数交给 worker thread。
4. Thread pool 自己也有容量，线程侧同样需要 bounded concurrency 思维。
5. 共享 legacy client object 前必须确认 thread-safe。
6. I/O-bound 与 CPU-bound 要先分类，再选方案。
7. Heartbeat 可以用来验证 Event Loop 是否仍能持续 scheduling。

## 关键问题

1. synchronous call 在本课里是什么意思？
2. blocking I/O 为什么会影响其他 Task？
3. `to_thread()` 把哪部分工作移出了 Event Loop thread？
4. CPU 与 CPU-bound 分别是什么意思？
5. worker thread 与 thread pool 分别是什么？
6. I/O-bound 与 CPU-bound 的区别是什么？
7. API 与 SDK 分别是什么？
8. thread-safe 是什么意思？
9. 为什么旧 client object 可能不能被多个 thread 同时共享？
10. 为什么 `to_thread()` 不是 CPU-bound 的通用答案？
11. heartbeat 为什么能帮助发现 Event Loop 被拖住？

## 场景命题

包装一个内部会 `time.sleep()` 的 legacy loader，批量加载多个 profile。

要求：

- Event Loop 仍能 scheduling heartbeat；
- loader 在线程侧执行；
- 同时调用 loader 的 worker thread 数量有明确上限；
- 不假设 legacy client 天然 thread-safe。

## 验收

测试会：

- 运行 heartbeat，确认 blocking 调用期间仍产生 tick；
- 记录 loader 在线程侧的 active / peak；
- 确认 peak 不超过设定限制；
- 验证所有 profile 结果正确。

仓库参考实现：

```bash
uv run pytest lessons/09_blocking_io/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/09_blocking_io/tests -v --learner
```
