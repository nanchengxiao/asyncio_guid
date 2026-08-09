# Lesson 03 — Structured concurrency

## 本节目标

学完本节，你应该能够：

- 为每个 Task 指定 owner（负责人）
- 解释 structured concurrency（结构化并发）的生命周期边界
- 使用 `TaskGroup` 管理一组兄弟 Task
- 理解一个子 Task 失败时，其余 Task 为什么会被请求取消

## 进入本课前

你已经从 Lesson 02 学过：Event Loop、Task、`create_task()`、并发和基本调度。

这一课第一次正式引入 **Task ownership、structured concurrency、TaskGroup、sibling task**。

## 为什么需要学习它

会创建 Task 之后，新的问题是：

> 这个 Task 到底归谁管？谁等它结束？它失败以后谁负责处理？父操作结束时它还能不能继续留在后台？

如果这些问题没有答案，代码虽然能跑，却很容易留下失控的后台任务。

## 核心理论

### 1. Task owner 是什么

这里的 **owner（负责人/拥有者）** 不是 Python 语法，而是设计概念：

> 哪一层业务代码负责创建这个 Task、等待它结束，并决定它失败或需要停止时怎么办。

如果一个 Task 被创建以后，谁都不再关心它，就可能变成 **orphan task（失去明确管理者的任务）**。

### 2. Structured concurrency 是什么

**Structured concurrency（结构化并发）** 的核心思想是：

> 并发创建出来的子任务，应当被限制在一个清楚的代码作用域内；离开这个作用域前，这些子任务必须已经收敛到结束状态。

Python 3.11 的 `asyncio.TaskGroup` 就是用来表达这种结构的：

```python
async with asyncio.TaskGroup() as tg:
    a = tg.create_task(step_a())
    b = tg.create_task(step_b())
# 运行到这里时，这个 TaskGroup 管理的子 Task 已经结束
```

### 3. sibling task 是什么

由同一个 `TaskGroup` 创建、处在同一层的子 Task，可以称为 **sibling tasks（兄弟任务）**。

如果其中一个 sibling 因普通异常失败，`TaskGroup` 会请求其余尚未结束的 sibling 停止，然后等待整个组收敛。

这里的“取消（cancel）”先理解成：**请求一个 Task 停止继续工作**。下一课会专门学习 cancellation 的具体机制。

### 4. TaskGroup 为什么要这样做

假设三个步骤共同组成一次业务操作，其中 A 已经失败，那么 B/C 继续跑可能已经没有意义。

```text
parent
  ├─ child A ── X 失败
  ├─ child B ───── 收到停止请求 → 清理 → 结束
  └─ child C ───── 收到停止请求 → 清理 → 结束
```

父操作不会在 B/C 还悬着时直接离开。

如果同时存在多个异常，Python 可以用 `ExceptionGroup` 表达“这里不止一个异常”。这一课只需要知道它是**能同时携带多个异常的异常对象**；Lesson 05 会正式学习如何处理它。

## 脑内执行模型

```text
父 Task 进入 TaskGroup
   ├─ sibling A ──────X failure
   ├─ sibling B ───────── stop request → cleanup
   └─ sibling C ───── stop request → cleanup

父 Task 等整个组结束后，才离开 TaskGroup
```

## 常见误解

- **误区：TaskGroup 只是 `gather()` 的新名字。** 它更强调“这些 Task 属于同一个作用域”和 sibling 失败时的统一收敛。
- **误区：创建 Task 后，只要以后某处可能 await 它就算管理清楚。** owner 应该从代码结构上就能定位。
- **误区：一个 sibling 失败后，其余 sibling 一定应该继续。** 如果它们共同组成一次业务操作，fail-fast（发现关键失败就尽快结束整组）通常更合理。
- **误区：TaskGroup 会把异常吃掉。** 它会等待子任务收敛，然后把失败向外传播。

## 本节规则总结

1. 每个 Task 都应有清楚的 owner。
2. Structured concurrency 把子 Task 限制在清楚的生命周期作用域中。
3. `TaskGroup` 会在离开作用域前等待其管理的子 Task 收敛。
4. 一个 sibling 失败时，其余 sibling 通常会收到停止请求。
5. 每个子任务自己的资源清理仍然要由自己保证。

## 关键问题

1. “谁拥有这个 Task”为什么是设计问题？
2. orphan task 有什么风险？
3. `TaskGroup` 离开作用域前保证了什么？
4. 一个 sibling 失败后，其余 sibling 为什么常常应该停止？
5. 什么情况下一个长期后台 Task 不适合放进短生命周期的 `TaskGroup`？

## 场景命题

启动三个兄弟 worker（这里的 worker 就是执行具体工作的子 Task）。其中一个会失败。

父操作必须等待整个组收敛；其他 worker 收到停止请求并执行自己的 cleanup，最终失败继续传给调用者。

## 验收

测试会观察 sibling 是否停止、cleanup 是否发生、异常是否继续传播，并确认函数返回后没有遗留本场景创建的 Task。

仓库参考实现：

```bash
uv run pytest lessons/03_structured_concurrency/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/03_structured_concurrency/tests -v --learner
```
