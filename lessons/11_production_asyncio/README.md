# Lesson 11 — Production asyncio

## 本节目标

学完本节，你应该能够：

- 设计 graceful shutdown 与 drain
- 区分 concurrency limit 与 rate limit
- 为 retry 设置明确条件和次数上限
- 理解 idempotency 的作用
- 使用基本日志和 metrics 观察系统
- 识别 task leak、slow downstream、retry storm

## 进入本课前

你已经学过 Task 生命周期、cancellation、timeout、Semaphore、Queue/backpressure、connection pool、blocking I/O 和业务 DAG。

本课新增：

- **rate limit（速率限制）**：限制单位时间内最多启动多少次调用。
- **retry（重试）**：失败后再次尝试；必须有适用条件和次数上限。
- **transient failure（暂时性失败）**：过一会儿再试可能恢复的失败，例如短暂网络故障。
- **idempotency（幂等性）**：同一个业务请求重复执行时，不产生重复副作用。
- **graceful shutdown（优雅关闭）**：停止服务时按明确策略收尾，而不是直接丢掉所有在途工作。
- **drain（排空）**：停止接收新工作，但把已经接收的工作处理完。
- **metrics（指标）**：用数字记录 received/succeeded/failed/retried 等系统状态。
- **structured logging（结构化日志）**：用“事件名 + 关键字段”记录日志，便于查询和分析。
- **task leak / retry storm**：本应结束的 Task 持续残留 / 大量失败请求同时重试并进一步放大故障。

## 为什么需要学习它

生产系统的问题通常来自多个机制相互影响：慢 downstream 让 Queue 增长，timeout 触发 retry，retry 又放大请求量，服务停止时还有在途 Task。毕业项目要求把这些边界放进同一个模型。

## 核心理论

最终流水线：

```text
输入
 ↓
bounded Queue
 ↓
固定数量 Workers
 ↓
API 并发闸门 + rate limiter
 ↓
External API（每次调用有 timeout + 有限 retry）
 ↓
写入并发闸门
 ↓
结果存储
```

**concurrency limit** 控制“同时在途多少调用”；**rate limit** 控制“单位时间启动多少调用”。它们必须分开。

Retry 只应对明确的 transient failure 生效，而且次数有限。每次 API attempt（一次尝试）仍应有自己的 timeout。

如果一次调用可能因为 timeout/retry 被重复执行，就必须考虑 idempotency。例如同一个 `job_id` 重复出现时，代码需要真的识别重复并避免重复写入；只有一个 ID 字段本身并不会自动产生幂等性。

本项目的 graceful shutdown 策略是：

```text
停止接收新输入
  ↓
等待 Queue drain
  ↓
worker 自然结束
  ↓
关闭资源并返回最终 metrics
```

日志至少应该让关键事件可见，例如 `job_retry`、`job_duplicate`；metrics 至少区分 received、succeeded、failed、retried、duplicates。

## 脑内执行模型

```text
RUNNING:  accept → queue → workers → api → writer
STOPPING: stop input → drain queue → workers end
STOPPED:  resources closed, final metrics ready
```

## 常见误解

- **误区：** rate limit=10 就等于 concurrency=10。一个控制启动速率，一个控制同时在途数量。
- **误区：** 失败就无限 retry 能提高成功率。可能形成 retry storm 并放大下游故障。
- **误区：** 有 `job_id` 就天然幂等。实现必须真的避免重复副作用。
- **误区：** graceful shutdown 就是 cancel 所有 worker。有些业务承诺要求先 drain 已接收工作。
- **误区：** metrics 只统计成功数即可。至少还要看失败、重试和重复等关键状态。

## 本节规则总结

1. bounded Queue 限制 backlog。
2. Semaphore/资源池限制 active concurrency。
3. rate limiter 限制启动速率。
4. 每次远程 attempt 有 timeout，retry 次数有限。
5. idempotency 防止重复副作用。
6. shutdown 顺序必须与业务承诺一致。
7. 日志和 metrics 要让 slow downstream、retry storm、task leak 可观察。

## 关键问题

1. concurrency limit 与 rate limit 分别控制什么？
2. 为什么 timeout + retry 可能形成流量放大器？
3. 哪些失败适合 retry？
4. idempotency 为什么不能只靠“调用者不要重复发送”？
5. drain shutdown 与 immediate cancel 的业务承诺有何区别？
6. queue size、worker count、API concurrency、writer concurrency 分别约束什么？
7. 哪些 metrics 能帮助发现 retry storm？
8. 什么现象会让你怀疑存在 task leak？

## 场景命题

先填写 `practice/DESIGN.md`，再实现 Job Processing Service：bounded Queue、固定 workers、API concurrency、rate limit、per-attempt timeout、有限 retry、`job_id` 幂等、有限 writer concurrency、graceful drain、日志与 metrics。

## 验收

测试覆盖重复 job、transient retry、资源峰值、调用启动间隔、drain 完成和最终 metrics；不依赖外部服务。

仓库参考实现：

```bash
uv run pytest lessons/11_production_asyncio/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/11_production_asyncio/tests -v --learner
```
