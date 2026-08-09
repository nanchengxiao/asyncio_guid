# Lesson 11 — Production asyncio

## 本节目标

学完本节，你应该能够：

- 设计 graceful shutdown 与 drain
- 区分 concurrency limit 与 rate limit
- 为 retry 设置明确条件和次数上限
- 理解 idempotency 为什么能降低重复执行的风险
- 使用基本日志和 metrics 观察系统状态
- 识别 task leak、slow downstream、retry storm

## 进入本课前

你已经学过：Task 生命周期、cancellation、timeout、ExceptionGroup、Semaphore、Queue/backpressure、connection pool、blocking I/O 和业务 DAG。

这一课把前面的能力组合起来，并新增 **graceful shutdown、drain、rate limit、retry、idempotency、metrics、structured logging、task leak、retry storm**。

## 为什么需要学习它

生产系统的问题往往不是某一个 API 写错，而是多个机制互相影响：

```text
下游变慢
  ↓
Queue 开始积压
  ↓
timeout 增多
  ↓
retry 增多
  ↓
请求量反而更大
```

同时，服务停止时可能还有已经接收但尚未处理完的工作。

毕业项目要求你把这些边界放进一个统一、可解释的模型。

## 核心理论

最终流水线：

```text
Input
  ↓
bounded Queue
  ↓
Workers
  ↓
API concurrency gate ── Rate limiter
  ↓
External API (per-attempt timeout + finite retry)
  ↓
Writer concurrency gate
  ↓
Result sink
```

### 1. concurrency limit 与 rate limit

你已经学过 **concurrency limit（并发上限）**：控制“同一时刻最多有多少个调用正在进行”。

本课新增 **rate limit（速率限制）**：

> 控制单位时间内最多允许启动多少个调用。

例如：

```text
concurrency = 3
```

表示同时最多 3 个在途请求。

```text
rate = 10 requests / second
```

表示平均一秒最多启动约 10 个请求。

两者不是一回事。

### 2. retry 是什么

**retry（重试）**就是一次调用失败后，再尝试执行。

但不能写成“所有失败无限重试”。合理 retry 至少要回答：

- 哪些错误允许 retry？
- 最多 retry 几次？
- 每次 attempt（尝试）是否有 timeout？
- 重复执行会不会造成重复副作用？

**transient failure（暂时性失败）**指“过一会儿再试可能恢复”的错误，例如短暂网络故障。它比参数错误、权限错误等永久性失败更适合 retry。

### 3. idempotency 是什么

**idempotency（幂等性）**可以先用业务语言理解：

> 同一个业务请求即使被重复执行，也不会产生重复副作用。

例如同一个 `job_id` 因网络超时被 retry 两次，系统仍只应该写入一次最终业务结果，而不是重复扣款、重复创建订单。

“有一个 job_id”本身不等于幂等；代码必须真的利用这个标识识别重复工作。

### 4. graceful shutdown 与 drain

**shutdown** 就是服务停止运行的过程。

**graceful shutdown（优雅关闭）**表示：

> 停止时遵守明确的业务收尾策略，而不是不管当前工作直接退出。

本项目采用的默认策略是：

```text
停止接收新工作
    ↓
继续处理已经接收的工作
    ↓
等待 Queue 被排空
    ↓
worker 结束
    ↓
关闭资源并返回最终统计
```

这里“继续处理已经进入系统的工作直到完成”就是 **drain（排空）**。

这和 immediate cancel（立即取消在途工作）是不同的业务承诺。

### 5. metrics 是什么

**metrics（指标）**是用数字持续记录系统状态，例如：

```text
received   收到多少 job
succeeded  成功多少
failed     失败多少
retried    发生多少次 retry
duplicates 发现多少重复 job
```

它的目标不是“为了有监控而记数字”，而是帮助回答：系统现在发生了什么？

### 6. structured logging 是什么

普通日志可能只是一句话：

```text
job failed
```

**structured logging（结构化日志）**会把事件名和关键字段清楚记录出来，例如：

```text
event=job_retry job_id=42 attempt=2 error=TimeoutError
```

这样机器和人都更容易查询、聚合和定位问题。

课程不引入大型日志框架，只要求形成“事件 + 关键字段”的基本意识。

### 7. task leak、slow downstream、retry storm

**task leak（Task 泄漏）**：本应结束的 Task 长期残留，数量不断增加。

**slow downstream（慢下游）**：你依赖的外部服务处理速度变慢，导致等待、Queue 积压或 timeout 增加。

**retry storm（重试风暴）**：下游已经出问题时，大量失败请求又同时 retry，反而制造更多流量，使故障更严重。

这些现象往往需要结合 Queue 长度、失败数、retry 数和在途 Task 数一起判断。

## 脑内执行模型

```text
RUNNING:
input → bounded queue → workers → API → writer

STOPPING:
停止新输入 → drain queue → worker 收敛 → 关闭资源

STOPPED:
没有遗留工作，最终 metrics 可读
```

## 常见误解

- **误区：rate limit=10 就等于 concurrency=10。** 一个控制单位时间启动量，一个控制同时在途数量。
- **误区：失败后多 retry 几次总能提高成功率。** 无上限 retry 可能形成 retry storm。
- **误区：有 `job_id` 就天然幂等。** 必须真的检查重复并避免重复副作用。
- **误区：graceful shutdown 就是 cancel 所有 worker。** 有些业务承诺要求先 drain 已经接收的工作。
- **误区：metrics 只统计成功数就够了。** 至少要区分接收、成功、失败、重试和重复等关键状态。

## 本节规则总结

1. bounded Queue 限制 backlog。
2. Semaphore/连接池限制 active concurrency。
3. rate limiter 限制单位时间启动量。
4. 每次远程 attempt 应有 timeout，retry 次数必须有限。
5. idempotency 用来降低重复执行造成重复副作用的风险。
6. shutdown 顺序必须对应业务承诺：drain 还是立即取消要明确。
7. 日志和 metrics 应能让 slow downstream、retry storm 和 task leak 变得可观察。

## 关键问题

1. concurrency limit 与 rate limit 分别控制什么？
2. 为什么 timeout + retry 可能形成流量放大器？
3. 哪些错误适合 retry，哪些明显不适合？
4. idempotency 为什么不能只靠“调用者不要重复发送”？
5. drain shutdown 与 immediate cancel 的业务承诺有何区别？
6. queue size、worker count、API concurrency、writer concurrency 各自约束什么资源？
7. 哪些 metrics 能帮助发现 retry storm？
8. task leak 是什么？你会观察哪些信号来怀疑它存在？

## 场景命题

先填写 `practice/DESIGN.md`，再实现 Job Processing Service：

- bounded Queue；
- 固定数量 workers；
- API concurrency limit；
- rate limit；
- 每次调用的 timeout；
- 有限 retry；
- `job_id` 幂等；
- writer concurrency limit；
- graceful drain；
- 日志与 metrics。

## 验收

测试会覆盖重复 job、暂时性失败 retry、资源峰值、调用启动间隔、drain 完成和最终 metrics；不依赖外部服务。

仓库参考实现：

```bash
uv run pytest lessons/11_production_asyncio/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/11_production_asyncio/tests -v --learner
```
