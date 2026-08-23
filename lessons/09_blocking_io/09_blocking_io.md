# Lesson 09 — 让会长时间等待的普通函数不要拖住其他工作

## 进入本课前

你已经学过 Event Loop、Task、thread、真实 async I/O 和 bounded concurrency。

## 本课新增术语

先把本课的词分成三组：识别工作为什么会卡住、把同步等待移到 worker thread、检查真实旧库的使用约束。看到完整例子前，只需要先分清这三层。

**第一组：先判断时间花在等待还是计算**

- **synchronous call（同步调用）**：像普通 Python 函数调用一样，当前执行路径会一直跑到这个调用返回，期间不会自动让别的 async 工作得到执行机会。
- **blocking I/O（阻塞式 I/O）**：synchronous call 在等待外部 I/O 时，当前 thread 仍被这个调用占住。
- **`time.sleep(seconds)`**：让调用它的当前 thread 同步停住约指定秒数；它不会像 `asyncio.sleep()` 那样把 Event Loop thread 的执行机会交回 asyncio。
- **I/O-bound（I/O 密集型）**：总时间主要花在等待外部 I/O，而不是持续做计算。
- **CPU（处理器）**：真正执行程序计算指令的硬件；本课只需要把它理解成“负责算东西的地方”。
- **CPU-bound（计算密集型）**：总时间主要花在 CPU 持续执行计算，而不是等待外部 I/O。

**第二组：用 thread 桥接 blocking I/O**

- **worker thread（工作线程）**：专门替 Event Loop thread 执行普通同步函数的另一条 thread。
- **thread pool（线程池）**：管理一组 worker thread 的容器；提交的同步工作会在线程可用时执行。
- **`asyncio.to_thread()`**：把一个普通同步函数交给 worker thread 执行，并让当前 Task 以 async 方式等待其结果的工具。
- **thread-safe（线程安全）**：同一个对象被多个 thread 同时使用时，内部状态仍能保持正确。

**第三组：真实 legacy library 的调用边界与观察信号**

- **API（接口）**：一个程序或库明确提供给其他代码调用的一组能力。
- **SDK（软件开发工具包）**：为了调用某个外部系统而提供的一组库、对象和 API。
- **legacy library（遗留/旧库）**：业务已经在使用、但设计时可能没有提供 asyncio API 的库。
- **client object（客户端对象）**：代码里代表某个外部系统调用入口的对象，例如旧 SDK 创建出来的 client。
- **heartbeat（心跳任务）**：周期性执行很小工作，用来观察 Event Loop 是否还能持续调度其他 Task。

## 一个例子串起全部术语

下面把一个只提供普通同步函数的旧数据加载器放进 worker thread，同时运行 heartbeat。只要 heartbeat 在加载期间仍持续打印，就能直接观察 Event Loop 没有被这段 blocking I/O 拖住。代码就是本课的 `case.py`：

```python
import asyncio
import time

THREAD_LIMIT = 2                  # thread pool 同样是有限 resource

def legacy_loader(profile_id):
    """旧 SDK 的普通同步函数：内部会长时间等待（blocking I/O）。"""
    print(f"[loader {profile_id}] worker thread 开始")
    time.sleep(0.3)
    print(f"[loader {profile_id}] worker thread 结束")
    return {"profile": profile_id, "data": "..."}

async def load_profile(profile_id, thread_semaphore):
    # to_thread 把同步函数交给 worker thread；当前 Task 只负责 async 等待结果
    async with thread_semaphore:
        return await asyncio.to_thread(legacy_loader, profile_id)

async def heartbeat():
    for _ in range(6):
        print("tick：Event Loop 仍在推进其他 Task")
        await asyncio.sleep(0.1)

async def main():
    thread_semaphore = asyncio.Semaphore(THREAD_LIMIT)
    tasks = []
    async with asyncio.TaskGroup() as tg:
        tg.create_task(heartbeat())
        for profile_id in (1, 2, 3):
            tasks.append(tg.create_task(load_profile(profile_id, thread_semaphore)))
    profiles = [task.result() for task in tasks]
    print(profiles)
    print(f"loader 线程并发上限 = {THREAD_LIMIT}；blocking 调用期间 heartbeat 未被拖住")

asyncio.run(main())
```

一次运行会看到 heartbeat 与数据加载处于同一段时间；相邻输出的具体交错可能略有变化：

```text
tick：Event Loop 仍在推进其他 Task
[loader 1] worker thread 开始
[loader 2] worker thread 开始
tick：Event Loop 仍在推进其他 Task
tick：Event Loop 仍在推进其他 Task
[loader 2] worker thread 结束
[loader 1] worker thread 结束
[loader 3] worker thread 开始
tick：Event Loop 仍在推进其他 Task
tick：Event Loop 仍在推进其他 Task
tick：Event Loop 仍在推进其他 Task
[loader 3] worker thread 结束
[{'profile': 1, 'data': '...'}, {'profile': 2, 'data': '...'}, {'profile': 3, 'data': '...'}]
loader 线程并发上限 = 2；blocking 调用期间 heartbeat 未被拖住
```

把本课知识点对到代码上：

| 术语或知识点 | 在这个例子里指什么 |
| --- | --- |
| **synchronous call** | `legacy_loader(profile_id)` 是普通函数调用；执行它的 thread 必须一直等到函数返回 |
| **blocking I/O** | `time.sleep(0.3)` 模拟旧函数等待外部结果时持续占住当前 worker thread |
| **`time.sleep(seconds)`** | 本例传入 `0.3`，真正停住执行 `legacy_loader()` 的 worker thread；它不会停住另一边的 Event Loop thread |
| **I/O-bound** | `legacy_loader()` 的大部分时间花在等待，而不是持续计算，因此适合用 `to_thread()` 桥接 |
| **CPU / CPU-bound** | 本例没有重计算；如果 0.3 秒都在执行大量 Python 计算，就不能机械地当成同一种问题 |
| **worker thread** | `asyncio.to_thread()` 选择另一条执行路径来运行 `legacy_loader()` |
| **thread pool** | `to_thread()` 背后管理 worker thread；本例再用 `thread_semaphore` 把同时提交并等待的 loader 调用限制为 2 |
| **`asyncio.to_thread()`** | 接收普通函数 `legacy_loader` 和参数 `profile_id`，返回一份可被当前 Task 异步等待的工作 |
| **thread-safe** | 最小例子没有共享可变 client object；真实 SDK 若在多个 worker thread 间共享对象，必须先确认这一保证 |
| **API** | `legacy_loader(profile_id)` 代表旧库对业务代码提供的一项可调用能力 |
| **SDK / legacy library** | 例子用 `legacy_loader()` 模拟一个业务已在使用、但没有 asyncio API 的旧 SDK |
| **client object** | 为保持例子最小，这里使用函数而没有共享 client；真实 `LegacyClient()` 若被共享，就要应用 thread-safe 检查 |
| **heartbeat** | `heartbeat()` 与三个加载 Task 都由同一个 `TaskGroup` 拥有，每约 0.1 秒打印一次 |
| **cancellation 边界** | 本例走正常结束路径；如果等待 `to_thread()` 的 Task 被取消，已经开始运行的同步函数通常仍会在线程里跑到返回 |

按时间线读输出：

1. `main()` 创建 `thread_semaphore`，再让同一个 `TaskGroup` 同时拥有 heartbeat 与 3 个 `load_profile()` Task。
2. 前两个加载 Task 取得 `thread_semaphore` 通行证；第三个在通行证外等待，所以本例同时提交的 loader 调用不超过 2。
3. 两次 `to_thread()` 把普通同步函数交给 worker thread，加载函数分别在那里执行 `time.sleep(0.3)`。
4. 两个加载 Task 在等待 worker thread 结果时没有占住 Event Loop thread，所以 heartbeat 仍能约每 0.1 秒打印 `tick`。
5. 第一批加载完成并归还通行证后，第三个加载 Task 才进入 `to_thread()`。
6. 三份 profile 都返回后，`TaskGroup` 退出，代码按保存的 Task 顺序组成结果列表。
7. Heartbeat 在整个阻塞等待期间持续推进；如果直接在 coroutine 中调用 `legacy_loader()`，这些 `tick` 会长时间停住。

## 本节目标

学完本节，你应该能够：

- 判断 synchronous call 是否会 blocking Event Loop thread；
- 使用 `asyncio.to_thread()` 桥接 blocking I/O；
- 区分 I/O-bound 与 CPU-bound；
- 解释 worker thread 与 thread pool 的作用；
- 解释为什么取消 async 等待不等于强制停止已经运行的 thread 函数；
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

### 5. Cancellation 不会强制杀死已经运行的 thread 函数

`asyncio.to_thread()` 让当前 Task 异步等待一个 thread 结果，但 Python 不能安全地在任意指令处强制终止已经开始运行的普通 thread 函数。

```text
Async Task 被 cancellation
        ↓
不再需要等待 to_thread 的结果

已经开始的 worker thread
        ↓
legacy_loader() 通常仍继续到自己返回
```

这意味着停止流程不能只看外层 Task 是否结束，还要知道同步函数是否可能仍占用文件、连接或其他 resource。本课示例只演示正常完成路径；真实 legacy API 如果需要可中止能力，必须使用它自己明确提供的停止机制。

还要注意：本例的 `thread_semaphore` 在正常路径上限制同时调用数。如果外层 Task 被取消，`async with` 可能先归还通行证，而底层已运行的 thread 仍未结束；因此不要把这个教学 Semaphore 误当成“可以强杀并精确管理 thread lifecycle”的工具。

### 6. 共享 client object 时要确认 thread-safe

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

### 7. I/O-bound 与 CPU-bound 先分类

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

### 8. Heartbeat 可以观察 Event Loop 是否被拖住

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

- **误区：** 取消等待 `to_thread()` 的 Task，会立即停掉同步函数。
  **更准确：** 已开始运行的 thread 函数通常仍会继续，直到它自己返回。

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
8. Cancellation 停止的是 async 等待关系，不保证强制终止已运行的同步 thread 函数。

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
12. 为什么取消 `await asyncio.to_thread(...)` 不等于同步函数已经停止？

## 场景命题

包装一个内部会 `time.sleep()` 的 legacy loader，批量加载多个 profile。

要求：

- Event Loop 仍能 scheduling heartbeat；
- loader 在线程侧执行；
- 同时调用 loader 的 worker thread 数量有明确上限；
- 不假设 legacy client 天然 thread-safe。

验收时让 loader 打印开始与结束，并与 heartbeat 输出交错；确认前两份 loader 可以重叠、第三份要等待 Semaphore 通行证。同时用文字回答：如果某个外层 Task 在 loader 已开始后被 cancellation，底层同步函数是否会立刻停止？

---

完成本课后：继续 [Lesson 10 — 先画清业务依赖，再决定工作怎样开始](../10_business_modeling/10_business_modeling.md)。
