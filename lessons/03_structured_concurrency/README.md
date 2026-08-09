# Lesson 03 — Structured concurrency

## 本节目标

学完本节，你应该能够：

- 为每个 Task 指定 owner
- 解释 structured concurrency 的生命周期边界
- 使用 `TaskGroup` 管理一组兄弟 Task
- 理解一个子 Task 失败时其余 Task 的收敛行为

## 进入本课前

你已经学过 Event Loop、Task、`create_task()`、并发和基本调度。

本课新增：

- **owner（负责人）**：负责创建、等待并处理某个 Task 生命周期的那一层代码。
- **structured concurrency（结构化并发）**：把子 Task 限制在清楚的代码作用域内，离开作用域前它们必须结束。
- **sibling tasks（兄弟任务）**：同一个父作用域管理的同层子 Task。
- **orphan task**：已经失去明确管理者、却还在运行的 Task。

## 为什么需要学习它

到处散落的 `create_task()` 最大问题通常不是语法，而是没人能回答：谁等待它？父操作结束后怎么办？异常去哪？Structured concurrency 把这些问题变成代码结构本身。

## 核心理论

```python
async with asyncio.TaskGroup() as tg:
    a = tg.create_task(step_a())
    b = tg.create_task(step_b())
# 到这里时，TaskGroup 管理的 child 已经结束
```

`TaskGroup` 就是一个清楚的 Task ownership 边界：父作用域创建 child，也负责等待 child。

一个 child 因普通异常失败时，TaskGroup 会请求其余尚未完成的 sibling 停止，然后等待整组收敛，再把失败向外传播。

这里的“取消”先理解成“请求 Task 停止”；Lesson 04 会正式讲 cancellation。

如果同时存在多个异常，Python 可以用 `ExceptionGroup`（一个能同时携带多个异常的异常对象）表达；Lesson 05 会正式处理它。

## 脑内执行模型

```text
parent owns TaskGroup
   ├─ child A ──────X failure
   ├─ child B ───────── stop → cleanup
   └─ child C ───── stop → cleanup

parent 等整个组收敛后才离开
```

## 常见误解

- **误区：** TaskGroup 只是 `gather()` 的新名字。它还编码了更清楚的生命周期和 sibling failure 语义。
- **误区：** 创建 Task 后只要最终某处 await 就算 ownership 清晰。owner 应在代码结构上可定位。
- **误区：** sibling 被停止一定是错误。如果它们共同组成一次业务操作，关键步骤失败后停止其余工作通常更合理。
- **误区：** TaskGroup 会吞异常。它会等待组内 Task 收敛，再把失败向外传播。

## 本节规则总结

1. 每个 Task 都应有清楚的 owner。
2. `TaskGroup` 把子 Task 放进明确的生命周期作用域。
3. 离开 TaskGroup 前，其管理的 child 已经收敛。
4. 一个 sibling 失败时，其余 sibling 通常会收到停止请求。
5. 每个 child 自己仍要负责资源 cleanup。

## 关键问题

1. 为什么“谁拥有这个 Task”是设计问题？
2. orphan task 有什么风险？
3. TaskGroup 中一个 child 失败，其余 child 会怎样？
4. 为什么父操作不应在 child 仍悬着时直接返回？
5. 哪类长期后台 Task 不适合放进短生命周期 TaskGroup？

## 场景命题

启动三个兄弟 worker（执行具体工作的子 Task）。其中一个会失败；父操作必须等待整组收敛，其余 worker 要停止并完成自己的 cleanup。

## 验收

测试会观察 sibling 是否停止、cleanup 是否执行、异常是否传播，并确认函数返回后没有遗留本场景创建的 Task。

仓库参考实现：

```bash
uv run pytest lessons/03_structured_concurrency/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/03_structured_concurrency/tests -v --learner
```
