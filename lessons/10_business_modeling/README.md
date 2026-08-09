# Lesson 10 — Business modeling

## 本节目标

学完本节，你应该能够：

- 使用六问模型分析一个异步业务
- 把业务依赖画成 DAG
- 在编码前决定 required / optional failure semantics
- 让 Task ownership 与业务依赖结构对齐

## 进入本课前

你已经学过：Task ownership、TaskGroup、timeout、cancellation、required/optional dependency、bounded concurrency、Queue/backpressure、真实 I/O。

这一课新增 **DAG、failure semantics、aggregator**。

## 为什么需要学习它

到这一阶段，API 已经不是最难的部分。

真正容易写乱的是：

- 哪些调用彼此独立？
- 哪些必须等待前一步结果？
- 哪些失败必须让整个请求失败？
- 哪些可以降级？
- Task 的生命周期应该怎样对应业务边界？

所以这一课先画业务模型，再写 asyncio 代码。

## 核心理论

### 1. DAG 是什么

**DAG（Directed Acyclic Graph，有向无环图）**听起来很数学，但在这门课里只需要把它理解成：

> 一张“谁依赖谁”的箭头图，而且依赖关系不会绕一圈又回到自己。

例如：

```text
user ──→ account
orders ──→ recommendations
```

箭头表示：右边的工作需要左边的结果。

如果两个节点之间没有依赖箭头，就可能有机会并发。

### 2. 六问模型

面对异步业务，先回答：

1. 工作单元是什么？
2. 谁依赖谁？
3. 哪些可以并发？
4. 并发上限是什么？
5. failure / timeout / cancellation 如何传播？
6. 每个 Task 的 owner 是谁？

这些答案比“这里用 gather 还是 TaskGroup”更早决定代码结构。

### 3. failure semantics 是什么

**failure semantics（失败语义）**就是：

> 某个步骤失败以后，业务上应该发生什么。

例如：

- account 是 required：失败后整个 dashboard 失败；
- recommendations 是 optional：失败后仍可返回 dashboard，只是没有推荐内容。

“捕不捕异常”是代码手段；“失败以后业务结果应该是什么”才是 failure semantics。

### 4. aggregator 是什么

本课场景是一个 **Async Service Aggregator（异步服务聚合器）**。

白话理解：

> 一个请求需要从多个服务取数据，再把这些数据组合成一个响应。

本课的依赖图：

```text
request
  ├─ user (required) ─────────→ account (required)
  └─ orders (required) ───────→ recommendations (optional)
```

第一层 `user` / `orders` 彼此无依赖，可以并发。

第二层：

- `account` 必须等 `user`；
- `recommendations` 必须等 `orders`；
- 这两个第二层调用彼此无依赖，所以满足各自前置条件后可以并发。

### 5. DAG 决定“最早启动时间”

不要看到 4 个 I/O 就立刻同时 `create_task()`。

一个节点最早能启动的时间是：

> 它依赖的所有前置结果都已经准备好以后。

所以业务 DAG 会直接决定 Task 何时创建。

### 6. Task ownership 应与业务边界对齐

如果一组 Task 共同完成“一次 dashboard 请求”，它们应该被这个请求的父作用域管理。

这样请求结束时，不会遗留一批仍在后台运行、但已经没人需要结果的 Task。

## 脑内执行模型

```text
T0: start user + orders
T1: user done ──────┐
    orders done ────┼─ start account + recommendations
T2: account required│ recommendations optional
T3: build response ◀┘
```

## 常见误解

- **误区：看见四个 I/O 就全部同时开始。** DAG 决定每个节点最早什么时候具备启动条件。
- **误区：optional 就是 `except Exception: pass`。** 只能隔离这个可选依赖定义好的失败，不能顺手吞掉 caller cancellation。
- **误区：DAG 只是画图，不影响代码。** 好的 TaskGroup 边界和 Task 创建时机应该反映依赖层次。
- **误区：业务建模会降低并发。** 它减少的是错误并发；真正独立的工作仍然应尽早重叠。

## 本节规则总结

1. 先画 DAG，再写 Task。
2. DAG 表达依赖，决定节点最早启动时间。
3. required / optional 属于 failure semantics。
4. Task owner 应对应一个清楚的业务操作边界。
5. DAG 只说明依赖；并发上限仍然来自资源容量。

## 关键问题

1. DAG 在这门课里用来表达什么？
2. 一个 DAG 节点最早什么时候可以启动？
3. failure semantics 与“写哪个 except”有什么区别？
4. recommendations optional 失败时，response 应该怎样表达？
5. account required 失败时，为什么通常不能把 dashboard 当成完整成功返回？
6. 为什么 Task ownership 应该与一次业务请求的生命周期对齐？
7. 如果两个节点虽然无依赖，却共用只有 2 条连接的资源池，还需要考虑什么？

## 场景命题

先填写 `practice/DESIGN.md`，再实现 Async Service Aggregator。

规则：

- user / orders：required，第一层并发；
- account：依赖 user，required；
- recommendations：依赖 orders，optional。

## 验收

测试会验证 DAG 启动顺序、第一层和第二层能够合理并发、optional failure 被隔离，以及 required failure 正确传播。

仓库参考实现：

```bash
uv run pytest lessons/10_business_modeling/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/10_business_modeling/tests -v --learner
```
