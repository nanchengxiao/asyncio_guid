# Lesson 11 — Production asyncio

## 本节目标

学完本节，你应该能够：

- 设计 graceful shutdown 与 drain
- 区分 concurrency limit 与 rate limit
- 为 retry 加入幂等性与上限
- 实现基本 structured logging / metrics
- 识别 task leak、slow downstream、retry storm

## 为什么需要学习它

生产系统的问题通常来自多个机制相互作用：慢下游让队列增长，timeout 触发 retry，retry 又放大 QPS，shutdown 时还有在途 Task。毕业项目要求把这些边界放进同一个可解释模型。

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

**Concurrency limit** 控制“同时在场多少调用”；**rate limit** 控制“单位时间最多启动多少调用”。它们必须分开。

Retry 只对明确的 transient failure 生效，次数有限，并要求 job_id 幂等，避免同一个业务工作因重试或重复输入被重复提交。

Shutdown 的默认策略是：停止接收新输入 → 等待 queue drain → worker 自然退出 → 返回 metrics。

## 脑内执行模型

```text
RUNNING: accept → queue → workers → api → writer
STOPPING: stop input | queue.join() | no orphan jobs
STOPPED: workers ended, resources closed, metrics final
```

## 常见误解

- **误区：** rate limit=10 就等于 concurrency=10。前者是每秒启动数，后者是同时在途数。
- **误区：** 失败就无限 retry 能提高成功率。会形成 retry storm 并放大下游故障。
- **误区：** 有 job_id 就天然幂等。实现必须真的避免重复副作用。
- **误区：** graceful shutdown 就是 cancel 所有 worker。很多服务更需要先 drain 已接收工作。
- **误区：** metrics 只记录成功数即可。至少要能区分 received/succeeded/failed/retried/duplicates。

## 本节规则总结

1. bounded queue 限制 backlog。
2. Semaphore/资源池限制 active concurrency。
3. Rate limiter 限制启动速率。
4. 每次远程 attempt 有 timeout，retry 次数有限。
5. 幂等 key 防止重复副作用。
6. shutdown 顺序必须与业务承诺一致。
7. 日志和 metrics 要让 slow downstream / retry storm 可见。

## 关键问题

1. concurrency limit 与 rate limit 的单位分别是什么？
2. 为什么 timeout + retry 可能形成放大器？
3. 哪些错误可以 retry，取决于哪些业务信息？
4. idempotency 为什么不能只靠“调用者不要重复发”？
5. drain shutdown 与 immediate cancel 的业务承诺有何区别？
6. queue size、worker count、API concurrency、writer concurrency 应分别由什么容量决定？
7. 哪些 metrics 能帮助识别 retry storm？
8. 如何判断存在 task leak？

## 场景命题

先填写 `practice/DESIGN.md`，再实现 Job Processing Service：bounded queue、固定 workers、API concurrency、QPS rate limiter、per-attempt timeout、有限 retry、job_id 幂等、有限 writer concurrency、graceful drain、日志与 metrics。

## 验收

测试覆盖重复 job、transient retry、资源峰值、rate spacing、drain 完成和最终 metrics；不依赖外部服务。

仓库参考实现：

```bash
uv run pytest lessons/11_production_asyncio/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/11_production_asyncio/tests -v --learner
```
