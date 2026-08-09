# Lesson 11 — 把前面机制组合成可运行服务

## 进入本课前

你已经学过 Task lifecycle、cancellation、timeout、Semaphore、bounded Queue、backpressure、connection pool、blocking I/O、DAG、retry、rate limit 和 drain。

本课不会重新定义这些词，而是在它们的基础上增加生产运行需要的约束。

## 本课新增术语

- **attempt（一次尝试）**：针对同一业务 operation 发起的一次具体调用；retry 会产生新的 attempt。
- **transient failure（暂时性失败）**：过一会儿再试有可能恢复的失败，例如短暂网络故障。
- **side effect（副作用）**：会改变外部状态的动作，例如写数据库、扣款、发送消息。
- **idempotency（幂等性）**：同一个业务请求被重复执行时，不会重复产生本不该重复的 side effect。
- **graceful shutdown（优雅关闭）**：服务停止时先按业务承诺处理在途工作和资源，再真正退出，而不是直接粗暴丢弃所有工作。
- **QPS（Queries Per Second，每秒请求数）**：每秒启动多少次请求的一种速率表达方式。
- **rate limiter（速率限制器）**：真正执行 rate limit 规则、决定某个新 request 现在能不能启动的控制组件。
- **writer（写入器）**：负责把处理结果写入数据库、文件或其他存储位置的处理环节。
- **metrics（指标）**：用数字持续记录系统状态，例如收到多少 job、成功多少、失败多少、retry 多少。
- **structured logging（结构化日志）**：用“事件名 + 明确字段”记录日志，让程序可以按字段查询和分析。
- **observability（可观测性）**：通过 metrics、日志等外部信号判断系统内部正在发生什么。
- **task leak（任务泄漏）**：本应结束的 Task 因生命周期管理错误长期残留并继续占用资源。
- **retry storm（重试风暴）**：大量失败请求在相近时间集中 retry，反而把已经有压力的 downstream 打得更重。

## 本节目标

学完本节，你应该能够：

- 设计 graceful shutdown，并明确什么时候需要 drain；
- 把 concurrency limit 与 rate limit 同时放进一个服务；
- 为每个 remote attempt 设置 timeout，并限制 retry 条件与次数；
- 解释 idempotency 为什么能保护重复执行；
- 限制 writer 的 resource capacity；
- 使用 metrics 与 structured logging 建立基本 observability；
- 识别 task leak、slow downstream 和 retry storm 的信号。

## 为什么需要学习它

生产问题通常不是某一个 asyncio API 单独出错，而是多个机制互相影响：

```text
slow downstream
    ↓
Queue 变长
    ↓
timeout 增多
    ↓
retry 增多
    ↓
downstream 压力更大
```

同时，服务还必须面对停止信号、重复 job、写入资源上限、长期运行中的 Task 生命周期，以及“出了问题之后怎么知道”。

最后一课的目标，就是把前面已经学过的独立机制组合成一个可解释的服务模型。

## 核心理论

### 1. 先画完整服务流水线

```text
输入
 ↓
bounded Queue
 ↓
固定数量 worker
 ↓
API concurrency gate + rate limiter
 ↓
External API
 ↓
writer concurrency gate
 ↓
结果存储
```

这里的 **gate（闸门）** 只是白话比喻：只有拿到许可的工作才能进入下一段受限资源区。

External API 中的 API 已在 Lesson 09 定义；这里表示“当前服务要调用的外部接口”。

### 2. Concurrency limit 与 rate limit 同时存在

前面已经分别学过：

- concurrency limit：控制同一时刻正在进行多少调用；
- rate limit：控制单位时间允许启动多少新调用。

生产服务里常常两个都需要。

例如：

```text
API concurrency = 5
QPS = 10
```

意思是：

- 同一时刻最多 5 个 API attempt 在途；
- 每秒最多启动 10 个新 attempt。

一个限制“同时占用量”，一个限制“启动速度”。

### 3. 每个 attempt 都要有自己的 timeout

假设一次业务 operation 最多 retry 2 次。

可能出现：

```text
attempt 1 → timeout
attempt 2 → transient failure
attempt 3 → success
```

每个 attempt 都应该有明确 timeout，否则其中一次调用可能无限等下去，导致整个 retry 策略失去边界。

所以：

```text
有限 retry 次数
    +
每次 attempt 有 timeout
    =
总等待时间才有可解释上界
```

### 4. 只对明确失败类型 retry

Retry 不能写成：

```python
except Exception:
    retry()
```

更合理的思路是先分类：

```text
transient failure → 可能适合 retry
明确业务错误    → 通常不 retry
caller cancellation → 不应当 retry
```

本课的重点不是列出所有错误类型，而是建立原则：

> retry 必须有适用条件和次数上限。

### 5. Retry 会带来重复执行，所以要考虑 idempotency

假设第一次 attempt 实际已经完成 side effect，只是 response 在网络途中丢失。

调用方看到 timeout 后 retry：

```text
attempt 1
└─ 已经写入成功
   └─ response 丢失

attempt 2
└─ 再次写入
```

如果没有 idempotency，就可能产生重复数据、重复扣款或重复消息。

常见做法是给业务请求一个稳定标识，例如 `job_id`，并在真正产生 side effect 前检查是否已经处理过。

但要注意：

> 只有 `job_id` 字段本身不会自动产生 idempotency；代码必须真的用它阻止重复 side effect。

### 6. Writer 也有 resource capacity

很多系统只限制 External API，却忘了最终写入数据库或文件同样可能成为瓶颈。

因此：

```text
很多处理结果
    ↓
writer concurrency limit
    ↓
有限写入资源
```

如果 writer 太慢，仍然可能导致上游 backlog 增长。

所以资源模型要覆盖整条 pipeline，而不是只盯住网络调用。

### 7. Graceful shutdown 先写业务承诺

本课采用的停止策略是：

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
服务结束
```

这就是 graceful shutdown：不是“永远不 cancel”，而是先明确哪些工作承诺处理完、哪些工作允许停止，再按顺序收尾。

有些服务可能选择立即停止剩余工作；那也是一种策略，但必须由业务承诺决定，而不是随手实现。

### 8. Metrics 让系统状态可以量化

最基础的 counters（计数器）可以包括：

```text
received
succeeded
failed
retried
duplicates
```

这里的 **counter（计数器）** 就是“只记录某类事件发生了多少次”的数字。

例如：

```text
retried 很快上涨
failed 也上涨
```

可能说明 downstream 正在持续失败，并且 retry 正在增加额外压力。

### 9. Structured logging 让单个事件可追踪

与只写：

```text
retrying
```

相比，更有用的是记录：

```text
event=job_retry job_id=123 attempt=2 reason=timeout
```

这样日志里能直接回答：

- 哪个 job？
- 第几次 attempt？
- 为什么 retry？

### 10. Observability 是为了从外部判断内部问题

如果出现 retry storm，可以观察：

- retry metrics 快速上涨；
- downstream failure 同时增加；
- Queue 长度持续升高；
- structured logging 中出现大量相似 retry event。

如果出现 task leak，可以观察：

- 已完成业务数量稳定，但存活 Task 数持续上升；
- 服务准备 shutdown 时总有本应结束的 Task 残留；
- 某些 Task 已经没有明确 owner。

Observability 的目标不是“日志越多越好”，而是：

> 关键业务状态和资源压力，能否从外部信号中被看见。

## 脑内执行模型

正常运行：

```text
RUNNING
accept input
    ↓
Queue
    ↓
workers
    ↓
API gate + rate limiter
    ↓
writer gate
    ↓
result stored
```

停止过程：

```text
STOPPING
stop new input
    ↓
drain accepted work
    ↓
workers end
    ↓
resources close
    ↓
final metrics
    ↓
STOPPED
```

失败恢复：

```text
attempt
  ├─ success → continue
  ├─ transient failure → maybe retry if attempts remain
  ├─ permanent failure → fail job
  └─ cancellation → propagate stop
```

## 常见误解

- **误区：** QPS=10 就等于 concurrency=10。  
  **更准确：** QPS 表达启动速率；concurrency 表达同时在途数量。

- **误区：** 失败就无限 retry 能提高成功率。  
  **更准确：** 这可能形成 retry storm，并放大 downstream 故障。

- **误区：** 每个 retry 共享一个无限等待的 attempt 也没关系。  
  **更准确：** 每次 attempt 自己仍应有 timeout。

- **误区：** 有 `job_id` 就天然 idempotent。  
  **更准确：** 实现必须真的利用稳定标识避免重复 side effect。

- **误区：** graceful shutdown 就是 cancel 所有 worker。  
  **更准确：** 是否 drain 已接收工作取决于业务承诺。

- **误区：** 只限制 External API concurrency 就够了。  
  **更准确：** writer 和其他有限资源同样可能成为瓶颈。

- **误区：** metrics 只统计成功数即可。  
  **更准确：** 至少还要能看到失败、retry、duplicate 和 backlog 等关键状态。

- **误区：** structured logging 就是写更多字符串。  
  **更准确：** 关键是事件名和字段结构稳定、可查询。

## 本节规则总结

1. 把整条 pipeline 的 resource capacity 都画出来。
2. Concurrency limit 与 rate limit 是两个独立限制。
3. 每个 remote attempt 都有自己的 timeout。
4. Retry 只对明确适合的 failure 生效，而且次数有限。
5. Retry 可能重复执行，所以要用 idempotency 防止重复 side effect。
6. Writer 也有自己的 concurrency capacity。
7. Graceful shutdown 顺序必须与业务承诺一致；需要时先 drain。
8. Metrics 与 structured logging 一起提供基础 observability。
9. Retry storm 与 task leak 都应该有可观察信号。

## 关键问题

1. attempt 与 retry 的关系是什么？
2. transient failure 为什么可能适合 retry？
3. side effect 在本课里指什么？
4. idempotency 为什么不能只靠“调用者不要重复发送”？
5. QPS 与 concurrency limit 分别控制什么？
6. rate limiter 负责什么？
7. 为什么每次 attempt 自己仍要有 timeout？
8. writer 为什么也需要资源上限？
9. graceful shutdown 与 drain 的关系是什么？
10. metrics 与 structured logging 分别提供什么信息？
11. observability 的目标是什么？
12. 哪些信号会让你怀疑出现 retry storm？
13. 哪些现象会让你怀疑存在 task leak？

## 场景命题

先填写 `practice/DESIGN.md`，再实现 Job Processing Service。

服务必须明确：

- bounded Queue；
- 固定数量 worker；
- API concurrency limit；
- QPS / rate limit；
- per-attempt timeout；
- 有限 retry；
- `job_id` idempotency；
- writer concurrency limit；
- graceful shutdown + drain；
- structured logging 与 metrics。

## 验收

测试会覆盖：

- duplicate job 不重复产生 side effect；
- transient failure 只在允许条件下有限 retry；
- 每个 attempt 有 timeout；
- API active peak 不超过 concurrency limit；
- attempt 启动间隔符合 rate limit；
- writer active peak 不超过 writer limit；
- shutdown 时已接收工作完成 drain；
- 最终 metrics 正确；
- 测试不依赖外部服务。

仓库参考实现：

```bash
uv run pytest lessons/11_production_asyncio/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/11_production_asyncio/tests -v --learner
```
