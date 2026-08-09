# Lesson 10 — 先画清业务依赖，再决定工作怎样开始

## 进入本课前

你已经学过 Task ownership、TaskGroup、timeout、cancellation、required / optional dependency、resource capacity、backpressure、connection pool 和 blocking I/O。

## 本课新增术语

- **six-question model（六问模型）**：编码前固定回答六类设计问题的检查表，用来把业务要求先翻译成执行结构。
- **node（节点）**：依赖图中的一个业务工作单元，例如“获取 user”或“获取 orders”。
- **edge（依赖箭头）**：表示一个 node 必须先拿到另一个 node 的结果才能开始。
- **DAG（Directed Acyclic Graph，有向无环图）**：一张用 node 和 edge 表示“谁依赖谁”的图，而且依赖不会绕一圈回到自己。
- **failure semantics（失败语义）**：某个 node 失败后，业务上应该整体失败、degradation，还是继续处理其他结果。
- **aggregator（聚合器）**：从多个来源取得数据，再把它们组合成一个业务结果的那层代码。

## 本节目标

学完本节，你应该能够：

- 使用 six-question model 分析异步业务；
- 把业务 data dependency 画成 DAG；
- 在编码前决定 required / optional failure semantics；
- 让 Task ownership 与业务边界对齐；
- 根据 DAG 判断每个 node 最早什么时候可以开始。

## 为什么需要学习它

到这一阶段，API 已经不再是最难的部分。

真正复杂的是业务本身：

- 哪些步骤彼此独立？
- 哪些步骤必须等上游结果？
- 哪些失败会让整个请求失效？
- 哪些失败可以 degradation？
- 哪些步骤共享同一个稀缺资源？
- 谁拥有每个 Task？

如果这些问题没有先回答，代码很容易变成“看到 I/O 就 create_task”，最后得到错误的 concurrency 结构。

## 核心理论

### 1. 先回答 six-question model

面对一个异步业务，编码前先回答：

1. 工作单元是什么？
2. 谁依赖谁？
3. 哪些工作可以同时开始？
4. 稀缺资源的并发上限是什么？
5. failure / timeout / cancellation 分别怎样影响业务结果？
6. 每个 Task 的 owner 是谁？

这六问不是新的 asyncio API，而是一套先做业务建模的顺序。

### 2. 用 DAG 表示 data dependency

本课的 aggregator 需要四份数据：

- user：required；
- orders：required；
- account：依赖 user，required；
- recommendations：依赖 orders，optional。

DAG：

```text
request
  ├─ user (required) ─────────→ account (required)
  └─ orders (required) ───────→ recommendations (optional)
```

箭头表达的是：

```text
user ─→ account
```

意思不是“user 和 account 有关系”这么模糊，而是：

> account 在拿到 user 结果前不能开始。

### 3. DAG 决定 node 最早启动时间

第一层：

```text
user
orders
```

二者只共享 request 输入，彼此没有 data dependency，所以可以同时开始。

第二层：

```text
account         ← 等 user
recommendations ← 等 orders
```

一旦各自前置结果准备好，它们就可以开始；account 不需要等 recommendations，反过来也一样。

所以 DAG 的核心价值是回答：

> 每个 node 最早什么时候具备开始条件？

### 4. DAG 不等于资源上限

即使 DAG 允许两个 node 同时开始，也不代表它们一定应该无限 concurrency。

例如两个 node 都访问同一个只有少量连接的 downstream，那么还要同时应用前面学过的 resource capacity 限制。

所以要分开：

```text
DAG               → 业务依赖允许什么时候开始
resource capacity → 资源最多允许多少工作同时占用
```

### 5. Failure semantics 先于 `except`

先决定业务规则，再写异常代码。

例如：

```text
account failure
→ required
→ 当前完整业务结果不能成立

recommendations failure
→ optional
→ 可以 degradation
```

不要反过来先写：

```python
except Exception:
    ...
```

然后再临时决定“这个异常好像可以忽略”。

`except` 是实现手段；failure semantics 是业务规则。

### 6. Optional 不代表可以吞掉 cancellation

Recommendations 是 optional，只表示它的业务结果可以缺失。

如果整个 request 已经收到 cancellation，上层根本不再需要结果，就不应该因为 recommendations optional 而继续吞掉 cancellation。

所以需要继续保持前面建立的规则：

```text
optional failure → 可以 degradation
caller cancellation → 继续 propagation
```

### 7. Task ownership 应与业务边界一致

一次 request 创建的短生命周期 Task，通常应该由这次 request 对应的代码边界负责。

不要让 request 已经返回，但它创建的业务 Task 还在后台孤立运行。

如果某份工作确实需要超过 request 生命周期，就必须有一个更长生命周期、明确的 owner 接管它。

## 脑内执行模型

```text
T0: start user + orders

T1: user done ─────────────→ start account
    orders done ───────────→ start recommendations

T2: account required
    recommendations optional

T3: apply failure semantics
    build response
```

同时还要叠加资源限制：

```text
DAG 允许开始
    ↓
资源是否还有容量？
    ↓
有 → 真正进入 downstream
无 → 等待资源
```

## 常见误解

- **误区：** 看见四个 I/O 就全部同时开始。  
  **更准确：** DAG 决定每个 node 最早启动时间。

- **误区：** DAG 只是画图，不影响代码。  
  **更准确：** Task 创建时机应该反映 edge 表达的 dependency。

- **误区：** optional 就是 `except Exception: pass`。  
  **更准确：** optional 只说明业务允许 degradation，不代表能吞掉 caller cancellation。

- **误区：** failure semantics 就是“异常怎么写”。  
  **更准确：** 它先决定业务结果，再决定用什么异常结构实现。

- **误区：** DAG 已经决定了 concurrency 上限。  
  **更准确：** DAG 决定依赖；resource capacity 决定同时能占用多少资源。

- **误区：** 业务建模会降低 concurrency。  
  **更准确：** 它减少错误 concurrency；真正独立的工作仍应尽早重叠等待。

## 本节规则总结

1. 先用 six-question model 理清业务，再写 Task。
2. DAG 用 node 和 edge 表达 data dependency。
3. DAG 决定 node 最早什么时候可以开始。
4. Required / optional 属于 failure semantics。
5. Failure semantics 应先于具体 `except` 写法。
6. Optional failure 可以 degradation，但不能顺手吞 caller cancellation。
7. Task owner 应对应清楚的业务生命周期。
8. DAG 与 resource capacity 是两条不同约束。

## 关键问题

1. six-question model 的六个问题是什么？
2. node 与 edge 在 DAG 中分别表示什么？
3. DAG 为什么不能有“绕一圈回到自己”的 dependency？
4. 一个 node 最早什么时候可以开始？
5. failure semantics 与“写哪个 except”有什么区别？
6. recommendations optional 失败时应该怎样处理？
7. account required 失败时为什么通常不能当成完整成功？
8. 如果两个 node 无 dependency，却共用同一个小连接池，还要考虑什么？
9. Task ownership 为什么应该跟业务生命周期对齐？

## 场景命题

先填写 `practice/DESIGN.md`，再实现 Async Service Aggregator。

业务关系：

- user：required；
- orders：required；
- account：依赖 user，required；
- recommendations：依赖 orders，optional。

要求：

- user / orders 第一层尽早同时开始；
- account 只能在 user 完成后开始；
- recommendations 只能在 orders 完成后开始；
- optional failure 可以 degradation；
- required failure 继续向外报告；
- caller cancellation 不能被 optional 处理吞掉。

## 验收

测试会验证：

- DAG 启动顺序正确；
- 第一层等待确实重叠；
- 第二层遵守各自 dependency；
- optional failure 被正确隔离；
- required failure 正确向外报告；
- Task 生命周期没有越过业务 owner 边界。

仓库参考实现：

```bash
uv run pytest lessons/10_business_modeling/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/10_business_modeling/tests -v --learner
```
