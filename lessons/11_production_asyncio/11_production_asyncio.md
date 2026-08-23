# Lesson 11 — 把前面机制组合成长期运行的程序

## 进入本课前

你已经学过 Task lifecycle、cancellation、timeout、Semaphore、bounded Queue、backpressure、connection pool、blocking I/O、DAG、retry、rate limit 和 drain。

本课不会重新定义这些词，而是在它们的基础上增加长期运行程序需要的约束。

## 本课新增术语

- **shutdown（关闭流程）**：程序从“还在正常接收和处理工作”走到“停止运行”的整个过程。
- **graceful shutdown（优雅关闭）**：shutdown 时先按业务承诺处理已经开始的工作和 resource，再真正退出，而不是直接粗暴丢弃所有工作。
- **attempt（一次尝试）**：针对同一业务 operation 发起的一次具体调用；retry 会产生新的 attempt。
- **transient failure（暂时性失败）**：过一会儿再试有可能恢复的失败，例如短暂 network 故障。
- **permanent failure（持久性失败）**：再次立即尝试通常也不会改变结果的失败，例如明确的参数错误。
- **side effect（副作用）**：会改变外部状态的动作，例如写入数据、扣款、发送消息。
- **idempotency（幂等性）**：同一个业务 request 被重复执行时，不会重复产生本不该重复的 side effect。
- **QPS（Queries Per Second，每秒请求数）**：每秒启动多少次 request 的一种速率表达方式。
- **rate limiter（速率限制器）**：真正执行 rate limit 规则、决定某个新 request 现在能不能启动的控制组件。
- **gate（闸门）**：本课对“进入受限 resource 前必须先获得许可”的控制点的白话称呼。
- **writer（写入器）**：负责把处理结果写入文件或其他存储位置的处理环节。
- **counter（计数器）**：只记录某类事件累计发生了多少次的数字。
- **metrics（指标）**：用数字持续记录程序状态，例如收到多少 job、成功多少、失败多少、retry 多少。
- **structured logging（结构化日志）**：用“事件名 + 明确字段”记录日志，让程序可以按字段查询和分析。
- **observability（可观测性）**：通过 metrics、日志等外部信号判断程序内部正在发生什么。
- **task leak（任务泄漏）**：本应结束的 Task 因 lifecycle 管理错误长期残留并继续占用 resource。
- **retry storm（重试风暴）**：大量失败 request 在相近时间集中 retry，反而把已经有压力的 downstream 压得更重。

## 本节目标

学完本节，你应该能够：

- 设计 graceful shutdown，并明确什么时候需要 drain；
- 把 concurrency limit 与 rate limit 同时放进一个长期运行程序；
- 为每个外部调用 attempt 设置 timeout，并限制 retry 条件与次数；
- 区分 transient failure 与 permanent failure；
- 解释 idempotency 为什么能保护重复执行；
- 限制 writer 的 resource 容量；
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

### 3. 每个 attempt 都要有自己的 timeout

假设一次业务 operation 最多 retry 2 次。

可能出现：

```text
attempt 1 → timeout
attempt 2 → transient failure
attempt 3 → 成功
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

如果：

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

这里的 `event`、`job_id`、`attempt`、`reason` 都只是日志字段名。

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

- **误区：** structured logging 就是写更多字符串。  
  **更准确：** 关键是事件名和字段结构稳定、可查询。

## 本节规则总结

1. 把整条 pipeline 的 resource 容量都画出来。
2. Concurrency limit 与 rate limit 是两个独立限制。
3. 每个外部调用 attempt 都有自己的 timeout。
4. Retry 只对明确适合的失败类型生效，而且次数有限。
5. Retry 可能重复执行，所以要用 idempotency 防止重复 side effect。
6. Writer 也有自己的 concurrency limit。
7. Graceful shutdown 顺序必须与业务承诺一致；需要时先 drain。
8. Metrics 与 structured logging 一起提供基础 observability。
9. Retry storm 与 task leak 都应该有可观察信号。

## 关键问题

1. shutdown 与 graceful shutdown 有什么区别？
2. attempt 与 retry 的关系是什么？
3. transient failure 与 permanent failure 有什么区别？
4. side effect 在本课里指什么？
5. idempotency 为什么不能只靠“调用者不要重复发送”？
6. QPS 与 concurrency limit 分别控制什么？
7. rate limiter 负责什么？
8. gate 在本课里表示什么？
9. 为什么每次 attempt 自己仍要有 timeout？
10. writer 为什么也需要 resource 上限？
11. counter 与 metrics 有什么关系？
12. graceful shutdown 与 drain 的关系是什么？
13. metrics 与 structured logging 分别提供什么信息？
14. observability 的目标是什么？
15. 哪些信号会让你怀疑出现 retry storm？
16. 哪些现象会让你怀疑存在 task leak？

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
- `job_id` idempotency；
- writer concurrency limit；
- graceful shutdown + drain；
- structured logging 与 metrics。
