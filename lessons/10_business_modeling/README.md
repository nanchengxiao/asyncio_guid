# Lesson 10 — Business modeling

## 本节目标

学完本节，你应该能够：

- 使用六问模型分析异步业务
- 把业务依赖画成 DAG
- 在编码前决定 required / optional failure semantics
- 让 Task ownership 与业务边界对齐

## 进入本课前

你已经学过 Task ownership、TaskGroup、timeout、cancellation、required/optional dependency、资源容量和 backpressure。

本课新增：

- **DAG（Directed Acyclic Graph，有向无环图）**：在本课中就是一张“谁依赖谁”的箭头图，依赖不会绕一圈回到自己。
- **failure semantics（失败语义）**：某一步失败后，业务上应该失败、降级还是继续。
- **aggregator（聚合器）**：从多个服务取数据，再组合成一个响应的业务层。

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

第一层 user/orders 可并发；第二层只有拿到对应上游结果后才能启动。account 与 recommendations 彼此无依赖，所以满足各自前置条件后仍可并发。

DAG 决定一个节点**最早什么时候可以开始**。不要看到四个 I/O 就全部同时 `create_task()`。

required/optional 属于 failure semantics：例如 account 失败意味着 dashboard 无法成立，而 recommendations 失败可以选择返回降级结果。

Task owner 则应与一次业务操作的生命周期对齐，避免请求结束后仍遗留没人需要的后台 Task。

## 脑内执行模型

```text
T0: start user + orders
T1: user done ──────┐
    orders done ────┼─ start account + recommendations
T2: account required│ recommendations optional
T3: build response ◀┘
```

## 常见误解

- **误区：** 看见四个 I/O 就全部同时开始。DAG 决定最早启动时间。
- **误区：** optional 就是 `except Exception: pass`。不能因为降级而顺手吞掉 caller cancellation。
- **误区：** DAG 只是画图，不影响代码。Task 创建时机和 TaskGroup 边界应反映依赖层次。
- **误区：** 业务建模会降低并发。它减少的是错误并发，真正独立的工作仍应尽早重叠。

## 本节规则总结

1. 先画 DAG，再写 Task。
2. required/optional 是 failure semantics。
3. Task owner 应对应清楚的业务生命周期。
4. DAG 决定依赖，不决定资源并发上限。
5. 降级结果应该在业务响应中可解释。

## 关键问题

1. DAG 在本课里表达什么？
2. 一个节点最早什么时候可以启动？
3. failure semantics 与“写哪个 except”有什么区别？
4. recommendations optional 失败时应怎样处理？
5. account required 失败时为什么通常不能当成完整成功？
6. 如果两个节点无依赖，却共用同一个小连接池，还要考虑什么？

## 场景命题

先填写 `practice/DESIGN.md`，再实现 Async Service Aggregator：user/orders required 且并发；account 依赖 user 且 required；recommendations 依赖 orders 且 optional。

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
