# Lesson 11 — 把前面机制组合成长期运行的程序

## 进入本课前

你已经学过 Task lifecycle、cancellation、timeout、Semaphore、bounded Queue、backpressure、connection pool、blocking I/O、DAG、retry、rate limit 和 drain。

本课不会重新定义这些词，而是在它们的基础上增加长期运行程序需要的约束。

这是综合应用课，不要求第一次阅读就记住 153 行代码。第一遍先沿一条普通工作追踪“进入等待区 → 被取出处理 → 调用外部能力 → 保存结果”，再观察输入结束后已经接收的工作怎样处理完；第二遍分别追踪“再次尝试后恢复”“再次尝试也不恢复”“外部状态已改变但返回结果超时”三条失败路径，最后再看程序怎样用数字和日志记录结果。示例只使用有限的 7 条工作构造可稳定运行的缩小模型，不会真的启动一个永不退出的线上服务。

## 本课新增术语

这是综合课，词多但不是一张待背诵清单。先按“怎样结束与恢复”“怎样控制启动和 resource”“怎样从外部看见问题”三组建立位置感，随后再把每个词对到同一条 pipeline。

**第一组：停止、失败恢复与重复执行保护**

- **shutdown（关闭流程）**：程序从“还在正常接收和处理工作”走到“停止运行”的整个过程。
- **graceful shutdown（优雅关闭）**：shutdown 时先按业务承诺处理已经开始的工作和 resource，再真正退出，而不是直接粗暴丢弃所有工作。
- **attempt（一次尝试）**：针对同一业务 operation 发起的一次具体调用；retry 会产生新的 attempt。
- **transient failure（暂时性失败）**：过一会儿再试有可能恢复的失败，例如短暂 network 故障。
- **`ConnectionError`**：Python 内置的一种 connection 失败异常；本例把它明确归入可以有限 retry 的 transient failure。
- **permanent failure（持久性失败）**：再次立即尝试通常也不会改变结果的失败，例如明确的参数错误。
- **backoff（退避）**：一次失败后，不立刻发起下一次 attempt，而是先等待一段时间；连续失败时等待通常逐步增加。
- **jitter（随机扰动）**：在 backoff 时间上增加少量随机变化，避免很多 worker 或 service 实例在同一时刻一起 retry。
- **side effect（副作用）**：会改变外部状态的动作，例如写入数据、扣款、发送消息。
- **idempotency（幂等性）**：同一个业务 request 被重复执行时，不会重复产生本不该重复的 side effect。
- **set（集合）**：Python 中只保存不重复元素的容器；本例用它记录哪些 job id 已经产生过 side effect。

**第二组：启动速率、共享状态与 resource 控制**

- **QPS（Queries Per Second，每秒请求数）**：每秒启动多少次 request 的一种速率表达方式。
- **rate limiter（速率限制器）**：真正执行 rate limit 规则、决定某个新 request 现在能不能启动的控制组件。
- **gate（闸门）**：本课对“进入受限 resource 前必须先获得许可”的控制点的白话称呼。
- **shared state（共享状态）**：多份 Task 都能读写的同一份数据；如果修改步骤会相互打断，结果就可能不正确。
- **`asyncio.Lock()`**：同一时刻只允许一个 Task 进入其保护范围的工具，本课用它保护 rate limiter 的 shared state。
- **monotonic clock（单调时钟）**：只用于比较经过时间、不会因为系统日期调整而倒退的时钟；适合计算调度间隔。
- **`asyncio.get_running_loop().time()`**：取得当前 Event Loop 的 monotonic clock 数值；本例用它计算下一次允许启动的时刻。
- **writer（写入器）**：负责把处理结果写入文件或其他存储位置的处理环节。

**第三组：观察运行状态与识别系统风险**

- **counter（计数器）**：只记录某类事件累计发生了多少次的数字。
- **metrics（指标）**：用数字持续记录程序状态，例如收到多少 job、成功多少、失败多少、retry 多少。
- **structured logging（结构化日志）**：用“事件名 + 明确字段”记录日志，让程序可以按字段查询和分析。
- **observability（可观测性）**：通过 metrics、日志等外部信号判断程序内部正在发生什么。
- **task leak（任务泄漏）**：本应结束的 Task 因 lifecycle 管理错误长期残留并继续占用 resource。
- **retry storm（重试风暴）**：大量失败 request 在相近时间集中 retry，反而把已经有压力的 downstream 压得更重。

本例还会用到两种容易看混的普通 Python 写法：函数参数里的 `**fields` 会把额外的“字段名=值”参数收集成一个 dictionary；表达式里的 `2 ** n` 则表示 2 的 n 次方。它们都不是新的 asyncio 机制。

## 一个例子串起全部术语

最后一课把前面机制放进同一条 job pipeline：bounded Queue 接收输入，固定数量 worker 处理工作，每个 API attempt 同时受 rate limit、concurrency limit 和 timeout 约束，结果写入也有独立容量，最后通过 drain 完成 graceful shutdown。代码就是本课的 `case.py`：

```python
import asyncio

WORKERS = 3
QUEUE_MAXSIZE = 3                 # bounded Queue：backlog 上界
API_CONCURRENCY = 2               # 3 个 worker 中最多 2 个同时占用 API
QPS = 20                          # 每秒最多启动多少个新 attempt
ATTEMPT_TIMEOUT = 0.2             # 每个 attempt 自己的 time budget
MAX_RETRIES = 2                   # 首次 attempt 之外，最多再 retry 两次
BASE_RETRY_DELAY = 0.05           # 第一次 retry 前的 backoff
WRITER_CONCURRENCY = 2            # writer 也是有限 resource

class PermanentJobError(Exception):
    """再次立即调用也不会恢复的明确业务失败。"""

class RetriesExhaustedError(Exception):
    """可 retry 的失败已经用完全部 attempt。"""

def log(event, **fields):
    """structured logging：事件名 + 明确字段，而不是一段自由文本。"""
    parts = [f"event={event}"]
    for key, value in fields.items():
        parts.append(f"{key}={value}")
    print(" ".join(parts))

def build_runtime():
    """创建只属于本次 service 运行周期的控制器、状态与 metrics。"""
    return {
        "api_gate": asyncio.Semaphore(API_CONCURRENCY),
        "writer_gate": asyncio.Semaphore(WRITER_CONCURRENCY),
        "writer_stats": {"active": 0, "peak": 0},
        "rate_lock": asyncio.Lock(),
        "next_start": 0.0,
        "metrics": {
            "received": 0,
            "succeeded": 0,
            "failed": 0,
            "retried": 0,
            "duplicates": 0,
        },
        "processed_ids": set(),  # 已真正产生 side effect 的 job id
    }

async def wait_for_rate_slot(runtime):
    """让新 attempt 依次等到允许启动的时刻。"""
    interval = 1 / QPS
    loop = asyncio.get_running_loop()
    async with runtime["rate_lock"]:
        now = loop.time()
        wait = max(0.0, runtime["next_start"] - now)
        if wait > 0:
            await asyncio.sleep(wait)        # 有意在锁内等：后来的 Task 依次排在后面
        runtime["next_start"] = loop.time() + interval

async def external_api(job, attempt, runtime):
    # side effect 前先做幂等检查：重复执行不能产生重复副作用
    if job["id"] in runtime["processed_ids"]:
        runtime["metrics"]["duplicates"] += 1
        log("job_duplicate", job_id=job["id"])
        return {"id": job["id"], "duplicate": True}
    behavior = job["behavior"]
    if behavior == "permanent":
        raise PermanentJobError("参数错误")       # permanent failure：不 retry
    if behavior == "persistent":
        raise ConnectionError("持续网络故障")      # 看似暂时，但本次一直没有恢复
    if behavior == "transient" and attempt == 1:
        raise ConnectionError("网络抖动")          # transient failure：可 retry
    if behavior == "timeout_after_side_effect":
        if attempt == 1:
            runtime["processed_ids"].add(job["id"])
            await asyncio.sleep(1.0)               # side effect 已发生，但 response 永远等不到
        return {"id": job["id"]}
    runtime["processed_ids"].add(job["id"])
    await asyncio.sleep(0.05)
    return {"id": job["id"]}

async def call_with_retry(job, runtime):
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            async with runtime["api_gate"]:        # 先取得 active concurrency 许可
                await wait_for_rate_slot(runtime)   # 再让真正启动时刻服从 QPS
                async with asyncio.timeout(ATTEMPT_TIMEOUT):
                    return await external_api(job, attempt, runtime)
        except TimeoutError:
            reason = "timeout"
        except ConnectionError:
            reason = "transient"
        if attempt <= MAX_RETRIES:
            retry_delay = BASE_RETRY_DELAY * (2 ** (attempt - 1))
            runtime["metrics"]["retried"] += 1
            log("job_retry", job_id=job["id"], attempt=attempt,
                reason=reason, delay=f"{retry_delay:.2f}")
            await asyncio.sleep(retry_delay)       # 下一次 attempt 前先 backoff
    raise RetriesExhaustedError(f"job {job['id']} 重试次数用尽")

async def save(result, runtime):
    async with runtime["writer_gate"]:             # writer 有自己的容量边界
        stats = runtime["writer_stats"]
        stats["active"] += 1
        stats["peak"] = max(stats["peak"], stats["active"])
        try:
            await asyncio.sleep(0.08)               # 模拟比单次 API 启动间隔更慢的写入
        finally:
            stats["active"] -= 1

async def worker(queue, name, runtime):
    while True:
        job = await queue.get()
        try:
            if job is None:                        # sentinel：没有新工作了
                break
            try:
                result = await call_with_retry(job, runtime)
            except PermanentJobError as error:
                runtime["metrics"]["failed"] += 1  # permanent failure：不 retry
                log("job_failed", worker=name, job_id=job["id"],
                    reason="permanent", error=str(error))
            except RetriesExhaustedError as error:
                runtime["metrics"]["failed"] += 1
                log("job_failed", worker=name, job_id=job["id"],
                    reason="retries_exhausted", error=str(error))
            else:
                await save(result, runtime)         # writer 未知失败不会伪装成 API 失败
                runtime["metrics"]["succeeded"] += 1
        finally:
            queue.task_done()

async def main():
    queue = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
    runtime = build_runtime()
    async with asyncio.TaskGroup() as tg:
        for worker_number in range(WORKERS):
            tg.create_task(worker(queue, f"worker-{worker_number}", runtime))
        jobs = [
            {"id": 1, "behavior": "ok"},
            {"id": 2, "behavior": "ok"},
            {"id": 3, "behavior": "ok"},
            {"id": 4, "behavior": "timeout_after_side_effect"},
            {"id": 5, "behavior": "transient"},
            {"id": 6, "behavior": "persistent"},
            {"id": 7, "behavior": "permanent"},
        ]
        for job in jobs:                            # 停止接收新输入之前只到这里
            runtime["metrics"]["received"] += 1
            await queue.put(job)                    # Queue 满 → 生产侧自动放慢
        log("input_closed", received=runtime["metrics"]["received"])
        for _ in range(WORKERS):
            await queue.put(None)
        await queue.join()                          # graceful shutdown：drain 已接收工作
    log("shutdown_complete", writer_peak=runtime["writer_stats"]["peak"],
        writer_limit=WRITER_CONCURRENCY)
    print("最终 metrics:", runtime["metrics"])

asyncio.run(main())
```

一次运行可能看到下面的日志；并发下相邻事件的顺序和具体 `worker-*` 名称可以略有变化，但最终 counters 应保持一致。由于 bounded Queue 会让 producer 与 worker 交替推进，早期 `job_retry` 甚至可能出现在 `input_closed` 之前；这只表示 worker 已开始处理，而 producer 还在放入后续 job：

```text
event=input_closed received=7
event=job_retry job_id=5 attempt=1 reason=transient delay=0.05
event=job_retry job_id=6 attempt=1 reason=transient delay=0.05
event=job_retry job_id=4 attempt=1 reason=timeout delay=0.05
event=job_retry job_id=6 attempt=2 reason=transient delay=0.10
event=job_duplicate job_id=4
event=job_failed worker=worker-1 job_id=7 reason=permanent error=参数错误
event=job_failed worker=worker-2 job_id=6 reason=retries_exhausted error=job 6 重试次数用尽
event=shutdown_complete writer_peak=2 writer_limit=2
最终 metrics: {'received': 7, 'succeeded': 5, 'failed': 2, 'retried': 4, 'duplicates': 1}
```

把本课知识点对到代码上：

| 术语或知识点 | 在这个例子里指什么 |
| --- | --- |
| **shutdown** | `main()` 从停止产生新 job、发送 sentinel，一直走到所有 worker 结束的完整停止过程 |
| **graceful shutdown** | `await queue.join()` 先 drain 已接收 job，再离开 `TaskGroup`，而不是直接丢下仍在处理的工作 |
| **attempt** | `for attempt in range(...)` 的每次循环都是同一 job 的一次具体外部调用 |
| **显式测试数据** | `jobs` 中的 `behavior` 直接写出 `ok`、`transient`、`persistent` 等路径，不用对 job id 做取模运算让学习者猜行为 |
| **transient failure** | Job 5 下一次 attempt 恢复；job 6 虽被分类为可 retry 的连接故障，但本次始终没有恢复 |
| **`ConnectionError`** | `external_api()` 用它模拟 job 5 与 job 6 的连接故障；只有这个已分类类型进入 transient retry 路径 |
| **permanent failure** | Job 7 触发专用的 `PermanentJobError("参数错误")`，worker 直接记录失败而不 retry |
| **backoff** | 每次允许 retry 时先等待 `0.05 × 2^(attempt-1)` 秒，job 6 的两次等待依次约为 0.05 和 0.10 秒 |
| **jitter** | 为保持课程输出与时长稳定，最小例子没有加入随机变化；真实多实例 service 通常还要避免同步 retry |
| **side effect** | `runtime["processed_ids"].add(job["id"])` 代表外部状态已经被真正改变 |
| **idempotency** | Retry 前检查稳定的 job id；job 4 首次已产生 side effect，第二次只记录 duplicate，不重复执行 |
| **set** | `runtime["processed_ids"]` 是只保存唯一 job id 的集合，支持 `id in ...` 检查与 `.add(id)` 登记 |
| **QPS** | `QPS = 20` 表示每秒最多为约 20 次新 attempt 安排启动时刻 |
| **rate limiter** | `wait_for_rate_slot()` 根据 QPS 让 attempt 依次等到允许启动的时刻，相邻放行时刻至少相隔一个 `interval` |
| **gate** | 3 个 worker 共用容量为 2 的 `api_gate`，所以 worker 数不等于 API 容量；`writer_gate` 另行守住写入 resource |
| **shared state** | 所有 worker 共用 `runtime["next_start"]`，每次安排 attempt 都必须读写它 |
| **`asyncio.Lock()`** | `runtime["rate_lock"]` 一次只让一个 Task 负责“等到自己的时刻并推进下一时刻”；这里的等待有意位于锁内 |
| **monotonic clock** | `asyncio.get_running_loop().time()` 提供只用于计算间隔的时间值，不把系统日期当调度依据 |
| **writer** | `save(result, runtime)` 代表较慢写入；`writer_gate` 限制同时写入数量，`writer_stats` 实测 peak |
| **counter / metrics** | `received = succeeded + failed` 核对最终结果；`retried` 与 `duplicates` 记录可重叠事件，`writer_stats["peak"]` 另行记录 resource 峰值 |
| **structured logging** | `log()` 输出输入关闭、retry、失败、duplicate 和 shutdown 完成等事件；retry 还带有等待时长字段 |
| **额外日志字段** | `log(event, **fields)` 把 `job_id=...`、`reason=...` 等命名字段收集成 dictionary，随后稳定地输出每个字段 |
| **observability** | 日志指出具体 job 的路径，最终 metrics 给出总量，两者组合后才能解释结果 |
| **task leak** | 正常路径中没有 task leak：workers 都由 `TaskGroup` 拥有，并在函数返回前收到 sentinel、完成并结束 |
| **retry storm** | 固定 worker、rate limiter 与 `MAX_RETRIES` 给 retry 压力建立边界；metrics 与日志负责暴露异常增长 |
| **runtime ownership** | `build_runtime()` 在 `main()` 运行后创建 gates、Lock、状态和 metrics，避免下一次运行继承上次的可变全局状态 |
| **失败分类** | `PermanentJobError` 与 `RetriesExhaustedError` 分别表达两条已知 API 路径；writer 位于这些 `except` 之外，未知写入错误不会被误报成 API 业务失败 |

按时间线沿一条 job 的执行路径和整体 shutdown 读取：

1. `main()` 创建容量为 3 的 Queue 和 3 个长期 worker；输入更快时，`queue.put()` 会把 backpressure 传回生产侧。
2. Worker `get()` 一条 job 后调用 `call_with_retry()`，第一次循环就是 attempt 1。
3. 最多两个 worker 能同时通过 `api_gate`；attempt 取得许可后再由 rate limiter 等到允许启动的时刻，最后只给真正的外部调用套上 timeout。
4. 普通 job 调用成功后通过 `writer_gate` 保存结果，并增加 `succeeded` counter；最终日志中的 `writer_peak=2` 证明写入上限真实参与了运行。
5. Job 5 第一次遇到 transient failure，记录 backoff 时长并等待后，下一次 attempt 成功。
6. Job 6 的连接故障连续出现；首次 attempt 之外只允许两次 retry，三次都失败后记录 `retries_exhausted`，证明循环有终点。
7. Job 4 第一次已经登记 side effect，但等待 response 时 timeout；retry 时幂等检查识别相同 job id，只返回 duplicate 结果并增加 counter。
8. Job 7 遇到 permanent failure，不进入 retry 分支，直接记录 `job_failed`。
9. 每条 job 无论成功或失败，都在 `finally` 中执行 `queue.task_done()`，因此 `queue.join()` 的完成条件可信。
10. 输入结束时先记录 `input_closed`，再为每个 worker 放入一个 sentinel，并等待 Queue drain。
11. 三个 worker 全部结束后 `TaskGroup` 才退出并记录 `shutdown_complete`；日志同时报告 writer peak 与 limit，最终 metrics 是 7 条接收、5 条成功、2 条失败、4 次 retry、1 次 duplicate。

## 本节目标

学完本节，你应该能够：

- 设计 graceful shutdown，并明确什么时候需要 drain；
- 把 concurrency limit 与 rate limit 同时放进一个长期运行程序；
- 为每个外部调用 attempt 设置 timeout，并限制 retry 条件与次数；
- 区分 transient failure 与 permanent failure；
- 解释 idempotency 为什么能保护重复执行；
- 限制 writer 的 resource 容量；
- 解释 rate limiter 为什么要保护共享的下一次启动时间；
- 使用 metrics 与 structured logging 建立基本 observability；
- 识别 task leak、变慢的 downstream 和 retry storm 的信号。

## 为什么需要学习它

长期运行程序的问题通常不是某一个工具单独出错，而是多个机制互相影响：

```text
downstream 变慢
    ↓
Queue 变长
    ↓
timeout 增多
    ↓
retry 增多
    ↓
downstream 压力更大
```

同时，程序还必须面对 shutdown、重复 job、writer resource 上限、长期存在的 Task lifecycle，以及“出了问题之后怎么知道”。

最后一课的目标，就是把前面已经学过的独立机制组合成一个可解释的整体模型。

## 核心理论

### 1. 先画完整 pipeline

```text
输入
 ↓
bounded Queue
 ↓
固定数量 worker
 ↓
API concurrency gate + rate limiter
 ↓
外部 API
 ↓
writer concurrency gate
 ↓
结果存储
```

API 已在 Lesson 09 定义；这里的“外部 API”表示当前程序要调用的外部接口。

Gate 表示：只有满足对应 resource 限制的工作，才能进入下一段。

示例里的 `build_runtime()` 在 `main()` 已经运行后创建 Queue 之外的 gates、Lock、共享状态和 metrics。它们只属于这一次 service lifecycle；如果把这些可变对象长期放在模块全局，重复运行或测试时就可能继承上一次状态，让 ownership 变模糊。

### 2. Concurrency limit 与 rate limit 同时存在

前面已经分别学过：

- concurrency limit 控制同一时刻正在进行多少调用；
- rate limit 控制单位时间允许启动多少新调用。

长期运行程序里常常两个都需要。

例如：

```text
API concurrency = 5
QPS = 10
```

意思是：

- 同一时刻最多 5 个 API attempt 正在进行；
- 每秒最多启动 10 个新 attempt。

一个限制“同时占用量”，一个限制“启动速度”。

本课的 rate limiter 还需要安全安排“下一次允许启动的时间”。多份 Task 会竞争同一条启动时间线，所以 `wait_for_rate_slot()` 用 `asyncio.Lock()` 让它们逐个排队：

```python
loop = asyncio.get_running_loop()
async with runtime["rate_lock"]:
    now = loop.time()
    wait = max(0.0, runtime["next_start"] - now)
    if wait > 0:
        await asyncio.sleep(wait)
    runtime["next_start"] = loop.time() + interval
```

这次 `sleep()` **有意放在锁内**。拿到 Lock 的 Task 是当前队首：它等到允许时刻，把下一时刻推进一个 `interval`，然后释放 Lock；后来的 Task 才能接着计算自己的等待。这样实现简单、启动间隔直观，而且队首在等待时被 cancellation，不会留下一个无人使用的未来预留时刻。

这不是“所有 sleep 都应该放在 Lock 内”的通用规则。这里 Lock 保护的业务不变量就是“只有队首能等待并推进同一条启动时间线”，因此等待本身属于临界流程；代价是其他 Task 会在 Lock 外排队。另一类实现可以在短暂加锁时一次性预留各自的未来时刻，再到锁外等待，但必须额外处理 cancellation 造成的空槽、很远的预留和算法公平性。选择哪种形状，要先说清 limiter 的承诺。

本例还把顺序写成：

```python
async with runtime["api_gate"]:
    await wait_for_rate_slot(runtime)
    async with asyncio.timeout(ATTEMPT_TIMEOUT):
        ...
```

先取得 concurrency gate，再等到 rate slot，能保证 limiter 放行后马上开始外部调用，不会又在 gate 后面等待。代价是等待 rate slot 或 Lock 时会占一份 concurrency 许可；真实系统应根据下游规则、排队成本和 limiter 算法明确选择顺序，而不是认为两种限制可以随意交换。

### 3. 每个 attempt 都要有自己的 timeout

假设一次业务 operation 最多 retry 2 次。

可能出现：

```text
attempt 1 → timeout
attempt 2 → transient failure
attempt 3 → 成功
```

每个 attempt 的真实外部调用都应该有明确 timeout，否则其中一次调用可能无限等下去，导致整个 retry 策略失去边界。

所以：

```text
有限 retry 次数
    +
每次 attempt 有 timeout
    =
外部调用部分才有可解释上界
```

这还不是整个 job 的总时限：进入 Queue、等待 gate、等待 rate slot，以及真实系统可能加入的 retry 间隔，都可能额外耗时。如果业务要求 job 从接收到完成也有总 time budget，还需要在更外层建立 operation 级时间边界。

### 4. 只对明确的失败类型 retry

Retry 不能写成：

```python
except Exception:
    retry()
```

更合理的思路是先分类：

```text
transient failure     → 可能适合 retry
permanent failure     → 通常不 retry
调用者发来的 cancellation → 不应当 retry
```

本课的原则是：

> retry 必须有适用条件和次数上限。

失败分类还要落到明确异常类型上：`PermanentJobError` 直接表示已知的 permanent 业务失败，`ConnectionError` 才进入本例允许 retry 的 transient 路径。这样 worker 不需要用宽泛异常猜测失败含义。

`MAX_RETRIES = 2` 表示首次 attempt 之外最多再试两次，所以最多有三个 attempts。示例中的 job 6 连续三次连接失败，第三次后不会再打印 retry，而是明确进入 `retries_exhausted` 失败路径。

“Retry 已用尽”本身也是一种明确的失败分类，所以例子使用专用的 `RetriesExhaustedError`。Worker 只捕获这个类型来记录 `retries_exhausted`；如果代码内部意外抛出别的 `RuntimeError`，它不会被伪装成正常的业务失败。越接近长期运行的 service，异常类型越应该表达清楚“谁能处理它”。

即使允许 retry，也不要在失败后立刻紧密重发。本例使用简单的指数 backoff：

```text
第一次 retry 前 → 等待 0.05 秒
第二次 retry 前 → 等待 0.10 秒
```

等待逐步增加，给可能正在恢复的 downstream 留出时间。真实系统中，很多 service 实例可能在同一时刻失败；如果它们都使用完全相同的 backoff，就可能再次同时醒来。因此生产策略通常还会加入 jitter，把启动时刻稍微打散。

为了让课程运行时长和输出稳定，`case.py` 没有使用随机数实现 jitter，但这不表示生产系统可以忽略它。Rate limiter、有限 retry、backoff 和 jitter 解决的是彼此相关但不同的压力来源。

### 5. Retry 会带来重复执行，所以要考虑 idempotency

假设第一次 attempt 实际已经完成 side effect，只是 response 在 network 途中丢失。

调用者看到 timeout 后 retry：

```text
attempt 1
└─ 已经写入成功
   └─ response 丢失

attempt 2
└─ 再次写入
```

如果没有 idempotency，就可能产生重复数据、重复扣款或重复消息。

常见做法是给业务 request 一个稳定标识，例如 `job_id`，并在真正产生 side effect 前检查是否已经处理过。

但要注意：

> 只有 `job_id` 字段本身不会自动产生 idempotency；代码必须真的用它阻止重复 side effect。

本课的内存 `set` 只用来把判断过程演示清楚。真正跨进程、会重启的 service 通常需要把幂等记录放进持久化存储，并保证“检查是否处理过”与“登记 side effect”之间不会被并发请求穿透；否则进程重启或两个相同 request 同时到达时，仍可能重复执行。

### 6. Writer 也有 resource 容量

很多程序只限制外部 API，却忘了最终写入同样可能成为瓶颈。

因此：

```text
很多处理结果
    ↓
writer concurrency gate
    ↓
有限写入 resource
```

如果 writer 太慢，仍然可能导致 upstream backlog 增长。

所以 resource 模型要覆盖整条 pipeline，而不是只盯住外部调用。

本例把模拟写入设置得比相邻 API attempt 的启动间隔稍慢，并复用 Lesson 06 的 `active / peak / finally` 观测方式。这样 `shutdown_complete` 中的 `writer_peak=2 writer_limit=2` 能直接证明两件事：写入确实发生过重叠，而且实际同时写入数没有越过容量。`finally` 则保证普通失败或 cancellation 不会让 active 观测值永久多算。

失败边界也要按 pipeline 阶段区分。本例只在 `call_with_retry()` 周围捕获 `PermanentJobError` 与 `RetriesExhaustedError`；`save()` 放在这个 `except` 范围之外。于是一个未知 writer 错误会让 `TaskGroup` 明确失败，而不会被错误计入“API permanent failure”。真实业务也可以为 writer 设计 retry 或隔离策略，但必须单独决定，不能复用 API 的错误分类假装已经处理。

### 7. Graceful shutdown 先写业务承诺

本课采用的 shutdown 策略是：

```text
停止接收新输入
    ↓
让 Queue drain
    ↓
worker 处理完已接收 job
    ↓
关闭 client / writer 等 resource
    ↓
返回最终 metrics
    ↓
程序结束
```

这就是 graceful shutdown：不是“永远不 cancellation”，而是先明确哪些工作承诺处理完、哪些工作允许停止，再按顺序收尾。

`case.py` 使用有限的 7 条 job，把“输入结束”当作 shutdown 触发点，所以可以稳定运行和观察。真实长期 service 还需要把操作系统信号、服务框架关闭通知或管理员命令转换成“停止接收新输入”；这属于接入环境的边界，不在这个最小核心示例里伪造。

本例的 `external_api()` 与 `save()` 都是用 `asyncio.sleep()` 模拟的，因此没有真实 HTTP session、数据库连接池或文件句柄需要关闭。把它换成真实 client / writer 后，应当由 `main()` 或一个更外层的 service lifecycle 用 `async with` 拥有这些 resource，并在 Queue drain、worker 结束后关闭；不能因为示例里的模拟对象无需关闭，就省略真实 resource 的 cleanup 设计。

有些程序可能选择立即停止剩余工作；那也是一种 shutdown 策略，但必须由业务承诺决定，而不是随手实现。

### 8. Metrics 让程序状态可以量化

最基础的 counter 可以包括：

```text
received
succeeded
failed
retried
duplicates
```

这些只是字段名，例如 `retried` 这个 counter 表示“累计发生过多少次 retry”。

不同 counter 不一定互斥。本例的最终结果满足：

```text
received = succeeded + failed
       7 = 5 + 2
```

但 `retried=4` 是额外 attempt 事件，`duplicates=1` 是某条最终成功 job 走过的幂等分支；它们会与成功/失败 job 重叠，不能再全部加进 `received`。设计 metrics 时要先写清每个 counter 统计的是“job 最终分类”还是“过程中发生的事件”。

如果：

```text
retried 很快上涨
failed 也上涨
```

可能说明 downstream 正在持续失败，并且 retry 正在增加额外压力。

`case.py` 中的 dictionary counters 只用于单次进程内演示：程序重启后会清零，也不会自动汇总其他 service 进程。真实部署通常把 counters 交给专门的指标存储与汇总系统，并谨慎选择维度；像每个 `job_id` 这样取值数量可能无限增长的信息更适合放进日志，而不是给 metrics 制造海量独立标签。

### 9. Structured logging 让单个事件可追踪

与只写：

```text
retrying
```

相比，更有用的是记录：

```text
event=job_retry job_id=123 attempt=2 reason=timeout
```

这里的 `event`、`job_id`、`attempt`、`reason` 都只是日志字段名。

`def log(event, **fields)` 中的 `**fields` 会把调用时额外写下的命名字段收进一个 dictionary。例如 `log("job_retry", job_id=5, reason="timeout")` 进入函数后，`fields` 就保存 `job_id` 和 `reason`；随后统一输出“字段名=值”。这让不同事件可以携带不同字段，又保持同一个日志入口。

本例用 `print()` 让学习者不安装日志系统也能观察字段；真实 service 通常交给结构化日志工具输出机器可解析格式，并由日志系统补充时间、等级、service 实例等公共字段。教学重点是事件名与字段含义稳定，不是把 `print()` 当作生产日志基础设施。

这样日志里能直接回答：

- 哪个 job？
- 第几次 attempt？
- 为什么 retry？

### 10. Observability 是为了从外部判断内部问题

如果出现 retry storm，可以观察：

- retry metrics 快速上涨；
- downstream 的失败同时增加；
- Queue 中等待的 job 持续增加；
- structured logging 中出现大量相似 retry 事件。

如果出现 task leak，可以观察：

- 已完成业务数量稳定，但存活 Task 数持续上升；
- 程序准备 shutdown 时总有本应结束的 Task 残留；
- 某些 Task 已经没有明确 owner。

Observability 的目标不是“日志越多越好”，而是：

> 关键业务状态和 resource 压力，能否从外部信号中被看见。

## 脑内执行模型

正常运行：

```text
运行中
接收输入
    ↓
Queue
    ↓
workers
    ↓
API gate + rate limiter
    ↓
writer gate
    ↓
结果已保存
```

shutdown：

```text
停止中
停止接收新输入
    ↓
drain 已接收工作
    ↓
workers 结束
    ↓
resources 关闭
    ↓
得到最终 metrics
    ↓
已停止
```

失败恢复：

```text
attempt
  ├─ 成功              → 继续
  ├─ transient failure → 还有次数时可以 retry
  ├─ permanent failure → 当前 job 失败
  └─ cancellation      → 继续向上层传播停止信号
```

## 常见误解

- **误区：** QPS=10 就等于 concurrency=10。  
  **更准确：** QPS 表达启动速率；concurrency 表达同时进行的数量。

- **误区：** 失败就无限 retry 能提高成功率。  
  **更准确：** 这可能形成 retry storm，并放大 downstream 的压力。

- **误区：** 每个 retry 共享一个无限等待的 attempt 也没关系。  
  **更准确：** 每次 attempt 自己仍应有 timeout。

- **误区：** 有 `job_id` 就天然具备 idempotency。  
  **更准确：** 实现必须真的利用稳定标识避免重复 side effect。

- **误区：** graceful shutdown 就是对所有 worker 立刻发 cancellation。  
  **更准确：** 是否 drain 已接收工作取决于业务承诺。

- **误区：** 只限制外部 API concurrency 就够了。  
  **更准确：** writer 和其他有限 resource 同样可能成为瓶颈。

- **误区：** metrics 只统计成功数即可。  
  **更准确：** 至少还要能看到失败、retry、重复和 backlog 等关键状态。

- **误区：** 最终打印的所有 counters 都应该相加等于 `received`。
  **更准确：** `succeeded` / `failed` 是互斥结果；`retried` / `duplicates` 是过程中可与结果重叠的事件。

- **误区：** structured logging 就是写更多字符串。  
  **更准确：** 关键是事件名和字段结构稳定、可查询。

- **误区：** Worker 捕获宽泛的 `ValueError` / `RuntimeError`，再统一猜成某种业务失败最省事。
  **更准确：** 宽泛捕获会把 API、writer 或程序缺陷混在一起；应只在对应阶段捕获表达已知结果的专用异常，让未知错误继续暴露。

## 本节规则总结

1. 把整条 pipeline 的 resource 容量都画出来。
2. Concurrency limit 与 rate limit 是两个独立限制。
3. 每个外部调用 attempt 都有自己的 timeout。
4. Retry 只对明确适合的失败类型生效，而且次数有限。
5. Retry 前要 backoff；多实例场景通常还要用 jitter 打散同步重试。
6. Retry 可能重复执行，所以要用 idempotency 防止重复 side effect。
7. Writer 也有自己的 concurrency limit，并应通过 active / peak 等真实行为验证。
8. Graceful shutdown 顺序必须与业务承诺一致；需要时先 drain。
9. Metrics 与 structured logging 一起提供基础 observability；每个 counter 还要写清是否与其他 counter 互斥。
10. Retry storm 与 task leak 都应该有可观察信号。
11. Gates、Lock、共享状态和 metrics 应由明确的 service lifecycle 拥有，不要无意跨运行残留。
12. Lock 的范围由它保护的不变量决定；本例为了逐个放行 attempt，有意让队首在 Lock 内等待并推进启动时间。
13. Attempt timeout 不自动覆盖 Queue、gate、rate slot 等整个 job 等待时间。
14. 生产 idempotency 通常需要持久且并发安全的记录，内存 `set` 只适合演示原理。
15. 用专用异常表达 permanent failure 与 retry 用尽，并把 `except` 范围限制在对应 pipeline 阶段。
16. 示例中的模拟 I/O 不需要关闭，不代表换成真实 client 或 writer 后可以省略 lifecycle 与 cleanup。
17. 内存 dictionary 与 `print()` 适合演示 observability，不等于跨进程、跨重启的生产 metrics / logging backend。

## 关键问题

1. shutdown 与 graceful shutdown 有什么区别？
2. attempt 与 retry 的关系是什么？
3. transient failure 与 permanent failure 有什么区别？
4. backoff 与 jitter 分别解决什么问题？
5. side effect 在本课里指什么？
6. idempotency 为什么不能只靠“调用者不要重复发送”？
7. QPS 与 concurrency limit 分别控制什么？
8. rate limiter 负责什么？
9. gate 在本课里表示什么？
10. 为什么每次 attempt 自己仍要有 timeout？
11. writer 为什么也需要 resource 上限？哪一行输出证明本例确实触及了这个上限？
12. counter 与 metrics 有什么关系？
13. graceful shutdown 与 drain 的关系是什么？
14. metrics 与 structured logging 分别提供什么信息？
15. observability 的目标是什么？
16. 哪些信号会让你怀疑出现 retry storm？
17. 哪些现象会让你怀疑存在 task leak？
18. 为什么本例的 rate limiter 有意把 `sleep()` 放在 `asyncio.Lock()` 内？它换来了什么，又让其他 Task 在哪里等待？
19. `MAX_RETRIES = 2` 最多会产生几个 attempts？
20. 为什么本例先取得 API gate，再等待 rate slot？交换顺序可能带来什么现象？
21. 为什么每次 attempt 有 timeout，仍不能推出整个 job 一定在同样时间内结束？
22. 内存 `set` 为什么不足以实现跨进程、跨重启的生产 idempotency？
23. 为什么 `PermanentJobError` / `RetriesExhaustedError` 比捕获所有 `ValueError` / `RuntimeError` 更能保护错误分类？为什么 writer 位于这些 `except` 之外？
24. `def log(event, **fields)` 与表达式 `2 ** n` 中的 `**` 分别是什么意思？
25. 为什么本例使用 3 个 worker，却只给 API gate 2 张通行证？
26. 为什么 `received = succeeded + failed`，却不能再把 `retried` 与 `duplicates` 一起加进这个等式？

## 场景命题

实现一个 `Job Processing Service`。

这个练习名表示“持续接收 job、处理并保存结果的 service”。

程序必须明确：

- bounded Queue；
- 固定数量 worker；
- API concurrency limit；
- QPS / rate limit；
- 每个 attempt 的 timeout；
- 有限 retry；
- retry 用尽使用明确的失败类型，不把未知异常误分类；
- retry backoff，并说明多实例时 jitter 的作用；
- `job_id` idempotency；
- writer concurrency limit，并用实际 peak 验证；
- graceful shutdown + drain；
- structured logging 与 metrics。

练习至少覆盖这些可观察路径：

- 一个普通 job 首次成功；
- 一个 transient failure 在有限 retry 后恢复；
- 一个 transient failure 用尽所有 retry 后失败；
- 一个 permanent failure 完全不 retry；
- API permanent failure、retry 用尽与 writer 未知失败必须是三条不同路径；
- 一个 side effect 已发生但 response timeout 的 job，通过 idempotency 避免重复副作用；
- 输入关闭后先 drain，所有 worker 都结束，最后才打印 shutdown 完成；
- 最终 metrics 能与逐条结构化日志互相核对。

实现前先画出 Queue、worker、API gate、rate limiter、writer gate 的顺序，并明确每个可变对象由哪个 lifecycle 创建。实现后至少连续运行两次，确认第二次不会继承第一次的 metrics、幂等记录或 rate limiter 时间状态。

不要从空白文件一次写完整条 pipeline。建议按四个可运行关卡推进：

1. 先完成 bounded Queue、固定 worker、普通 API 成功与 writer；
2. 再加入 API concurrency limit、rate limit 和 attempt timeout；
3. 再加入明确失败分类、有限 retry、backoff 与 idempotency；
4. 最后加入 graceful shutdown、structured logging、metrics，并覆盖上面的验收路径。

每一关都先运行并确认输出，再进入下一关；这样出现问题时，只需要检查刚增加的一个机制。

---

完成本课后：回到 [Course Map](../../COURSE_MAP.md) 复盘整条路线，并选择仍无法用自己的话解释的 Lesson 重新运行 `case.py`。
