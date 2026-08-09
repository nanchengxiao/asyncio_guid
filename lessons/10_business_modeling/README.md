# Lesson 10 — Business modeling

## 本节目标

学完本节，你应该能够：

- 使用六问模型分析异步业务
- 把业务依赖画成 DAG
- 在编码前决定 required/optional failure semantics
- 让 Task ownership 与 DAG 对齐

## 为什么需要学习它

到这一阶段 API 已经不是核心。优秀的 asyncio 代码来自清楚的业务模型：哪些工作独立、谁依赖谁、资源上限在哪里、失败应该传播到哪里。

## 核心理论

面对业务先回答六问：

1. 工作单元是什么？
2. 谁依赖谁？
3. 哪些可以并发？
4. 并发上限是什么？
5. failure / timeout / cancellation 如何传播？
6. 每个 Task 的 owner 是谁？

本课 Aggregator 的 DAG：

```text
request
  ├─ user (required) ─────────→ account (required)
  └─ orders (required) ───────→ recommendations (optional)
```

第一层 user/orders 可并发；第二层只有拿到对应上游后才能启动。第二层 account/recommendations 彼此可并发。

## 脑内执行模型

```text
T0: start user + orders
T1: user done ──────┐
    orders done ────┼─ start account + recommendations
T2: account required│ recommendations optional
T3: build response ◀┘
```

## 常见误解

- **误区：** 看见四个 I/O 就全部同时 create_task。DAG 决定最早启动时间。
- **误区：** optional 只是捕获所有 Exception。应该只隔离该依赖自身定义的失败，并保留 cancellation。
- **误区：** DAG 只是画图，不影响代码。好的 TaskGroup 边界应反映 DAG 层次。
- **误区：** 业务建模会降低并发。它降低的是错误并发，独立工作仍应尽早重叠。

## 本节规则总结

1. 先画 DAG，再写 Task。
2. required/optional 是产品语义。
3. Task owner 应对应一个清楚的业务操作边界。
4. 并发上限来自资源，不来自 DAG 本身。
5. 任何降级都应在 response contract 中可解释。

## 关键问题

1. 六问模型中的 Task owner 为什么单独成问？
2. DAG 中一个节点最早何时可以启动？
3. recommendations optional 失败时 response 应如何表达？
4. account required 失败时为什么不应返回半成功 dashboard？
5. 如何避免捕获 optional failure 时吞掉 caller cancellation？
6. 如果第二层两个调用共用同一连接池，DAG 之外还要增加什么模型？

## 场景命题

先填写 `practice/DESIGN.md`，再实现 Async Service Aggregator。user/orders required 且并发；account 依赖 user 且 required；recommendations 依赖 orders 且 optional。

## 验收

测试验证 DAG 启动顺序、第一/第二层并发、optional 隔离与 required 传播。

仓库参考实现：

```bash
uv run pytest lessons/10_business_modeling/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/10_business_modeling/tests -v --learner
```
