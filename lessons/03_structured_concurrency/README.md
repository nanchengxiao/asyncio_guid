# Lesson 03 — Structured concurrency

## 本节目标

学完本节，你应该能够：

- 为每个 Task 指定 owner
- 解释结构化并发的生命周期边界
- 使用 TaskGroup 表达一组兄弟任务
- 理解一个子任务失败时 sibling 的取消语义

## 为什么需要学习它

到处散落的 `create_task()` 最大问题通常不是语法，而是没人能回答：谁等待它？父任务退出后怎么办？异常去哪？Structured concurrency 把这些问题变成代码结构本身。

## 核心理论

```python
async with asyncio.TaskGroup() as tg:
    a = tg.create_task(step_a())
    b = tg.create_task(step_b())
# 离开作用域时：所有 child 已结束，或失败已完成传播
```

TaskGroup 是一个 ownership boundary。父作用域创建 child，也负责等待 child；一个 child 以普通异常失败时，TaskGroup 会取消其余尚未完成的 child，然后把失败以 `ExceptionGroup` 形式传播。

## 脑内执行模型

```text
parent owns TaskGroup
   ├─ child A ──────X failure
   ├─ child B ───────── cancelled → finally
   └─ child C ───── cancelled → finally

parent 离开 TaskGroup 前，不会把这些 child 留在身后。
```

## 常见误解

- **误区：** TaskGroup 只是 gather 的新名字。它编码了更强的 sibling failure 与生命周期语义。
- **误区：** 创建 Task 后只要最终某处 await 就算 ownership 清晰。owner 应在结构上可定位。
- **误区：** 取消 sibling 是错误。对于同一操作的一组兄弟任务，这通常正是 fail-fast 所需语义。
- **误区：** TaskGroup 会吞掉异常。它会组合并向外传播。

## 本节规则总结

1. Task 必须属于一个可解释的生命周期边界。
2. TaskGroup 离开前会等待所有 child 收敛。
3. child 普通失败会触发 sibling cancellation。
4. cleanup 仍由每个 child 自己用 finally 保证。
5. 不要把长期后台服务误塞进短生命周期 TaskGroup。

## 关键问题

1. 为什么“谁拥有这个 Task”是设计问题而不是代码风格？
2. TaskGroup 中一个 child 失败，其余 child 会怎样？
3. 父 task 自己被取消时，child 应怎样收敛？
4. 什么时候裸 create_task 仍然合理？它的 owner 应在哪里？
5. 为什么结构化并发减少 orphan task？

## 场景命题

启动三个兄弟 worker，其中一个会失败。父操作必须等待整个组收敛，其他 worker 收到取消并执行 cleanup，最终向调用者传播失败。

## 验收

测试观测 sibling cancellation、cleanup 与异常传播；同时检查函数返回后没有遗留当前场景创建的 Task。

仓库参考实现：

```bash
uv run pytest lessons/03_structured_concurrency/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/03_structured_concurrency/tests -v --learner
```
