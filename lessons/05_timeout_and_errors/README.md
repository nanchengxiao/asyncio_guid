# Lesson 05 — Timeout and errors

## 本节目标

学完本节，你应该能够：

- 使用 `asyncio.timeout()` 建立时间上限
- 区分 timeout 与 cancellation 的业务语义
- 理解 `ExceptionGroup`
- 使用 `except*` 对并行失败分类
- 区分 required / optional 依赖

## 进入本课前

你已经学过 TaskGroup、sibling task、cancellation、`CancelledError` 和异常传播。

本课新增：

- **timeout（超时）**：超过允许等待的时间后不再继续等。
- **time budget（时间预算）**：允许某段工作最多使用的时间。
- **required / optional dependency**：失败后是否必须让当前业务整体失败的必需/可选依赖。
- **`ExceptionGroup`**：能够同时携带多个异常的异常对象。
- **`except*`**：从异常组中按类型选择并处理匹配异常的语法。

## 为什么需要学习它

真实调用不只有“成功/失败”。同一个 operation 可能成功、普通异常、超时或被上层取消。如果这些语义混在一起，后续的降级、重试和告警就很容易做错。

## 核心理论

```python
async with asyncio.timeout(0.5):
    result = await remote_call()
```

这里表示给这段工作约 0.5 秒的 time budget。超时时，作用域内部会借助 cancellation 停止等待，越过边界后调用者通常看到 `TimeoutError`。

所以：

```text
cancellation → 上层不再需要这份工作
timeout      → 时间预算耗尽，不能再等
```

业务依赖也要区分：

```text
order 数据：required → 失败后请求无法成立
推荐数据：optional  → 失败后可以返回降级结果
```

并行 sibling 可能在很接近的时间各自失败。TaskGroup 可以用 `ExceptionGroup` 保留多个失败：

```python
try:
    async with asyncio.TaskGroup() as tg:
        ...
except* ValueError as group:
    ...
```

`except* ValueError` 会从异常组中选出匹配 `ValueError` 的那部分，不是简单拿“第一个异常”。

**retry（重试）**就是失败后再尝试一次。本课只记住：timeout 不自动等于“应该 retry”；是否适合重复执行要看业务语义。

## 脑内执行模型

```text
operation
  ├─ success      → value
  ├─ exception    → 普通失败
  ├─ timeout      → 时间预算耗尽
  └─ cancellation → 上层不再需要工作
```

## 常见误解

- **误区：** timeout 与 cancellation 完全无关。asyncio timeout 会借助 cancellation 停止内部等待，但对外表达的是时间预算耗尽。
- **误区：** 超时就一定应该重试。要先判断错误类型和重复执行是否安全。
- **误区：** ExceptionGroup 只需要打印。它让多个并行失败可以被保留和分类。
- **误区：** optional 依赖失败必须让整个请求失败。required/optional 是业务规则。

## 本节规则总结

1. 远程调用应有明确的时间预算。
2. timeout、普通异常和 caller cancellation 要区分。
3. required / optional 是业务语义。
4. `ExceptionGroup` 可以保留多个并行失败。
5. `except*` 用于异常组的类型化处理。

## 关键问题

1. timeout 与 cancellation 的业务语义有什么不同？
2. `asyncio.timeout()` 超时后调用者通常看到什么？
3. 为什么并行 Task 可能需要 `ExceptionGroup`？
4. `except* ValueError` 做了什么？
5. required 与 optional dependency 应由谁决定？
6. 为什么 timeout 不能自动等价于 retry？

## 场景命题

实现一个 required operation 的时间预算，并实现一个并行失败收集函数。多个 sibling 失败时不能只保留第一个异常。

## 验收

测试会验证 timeout 边界、required 失败传播，以及多个并行失败没有被错误丢失。

仓库参考实现：

```bash
uv run pytest lessons/05_timeout_and_errors/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/05_timeout_and_errors/tests -v --learner
```
