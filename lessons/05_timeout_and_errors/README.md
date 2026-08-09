# Lesson 05 — Timeout and errors

## 本节目标

学完本节，你应该能够：

- 使用 `asyncio.timeout()` 给异步操作设置时间上限
- 区分 timeout 与 cancellation 的业务含义
- 理解 `ExceptionGroup` 为什么能同时保存多个异常
- 使用 `except*` 按异常类型处理并行失败
- 区分 required / optional 依赖

## 进入本课前

你已经学过：TaskGroup、sibling task、cancellation、`CancelledError` 和异常传播。

这一课新增 **timeout、time budget、ExceptionGroup、except*、required/optional dependency**。

## 为什么需要学习它

真实服务调用不只有“成功”和“失败”。一次异步操作可能：

```text
成功
普通异常
超时
被上层取消
```

这些结果的含义不同。如果全部混成一个“出错了”，后面就很难正确决定是否降级、是否再次尝试、是否告警。

## 核心理论

### 1. timeout 和 time budget

**timeout（超时）**表示：

> 这份工作超过允许等待的时间，就不再继续等。

这个允许的时间也常叫 **time budget（时间预算）**。

```python
async with asyncio.timeout(0.5):
    result = await remote_call()
```

这里表示最多给这个代码块约 0.5 秒。

`asyncio.timeout()` 内部会通过 cancellation 停止超时作用域里的等待；越过 timeout 边界后，调用者通常看到 `TimeoutError`。

所以：

- cancellation：上层主动说“我不要这份工作了”；
- timeout：时间预算耗尽，“不能再等了”。

两者底层有关联，但业务语义不同。

### 2. required / optional dependency

一个业务请求经常依赖多个下游服务。

**required dependency（必需依赖）**：它失败后，当前业务结果就无法成立。

**optional dependency（可选依赖）**：它失败后，业务仍可以返回一个降级结果。

例如：

```text
订单详情
├─ order 数据：required
└─ 推荐商品：optional
```

这是业务决定，不是 asyncio API 自动替你决定的。

### 3. ExceptionGroup 是什么

并行 Task 可能在很接近的时间各自失败。

如果只抛出“第一个异常”，其他失败信息就可能丢失。

`ExceptionGroup` 可以理解成：

> 一个里面装着多个异常的异常对象。

TaskGroup 会在需要时用它把一组并行失败一起向外传播。

### 4. `except*` 是什么

普通 `except` 面对的是一个异常；`except*` 是 Python 用来处理异常组的语法。

```python
try:
    async with asyncio.TaskGroup() as tg:
        ...
except* ValueError as group:
    ...
```

它会从异常组中选出匹配 `ValueError` 的那部分，而不是简单取“第一个异常”。

### 5. timeout 不等于一定要 retry

**retry（重试）**就是“失败后再执行一次”。

超时以后能不能安全重试，要看业务操作是否适合重复执行、错误是否可能只是暂时性的。比如“查询”通常比“扣款”更容易安全重试。

后面的生产课会更系统地讲 retry 和 idempotency；这一课只要求你不要把 `TimeoutError` 自动等价成“再来一次”。

## 脑内执行模型

```text
operation
  ├─ success      → 返回结果
  ├─ exception    → 普通业务/系统失败
  ├─ timeout      → 时间预算耗尽
  └─ cancellation → 上层不再需要这份工作
```

## 常见误解

- **误区：timeout 与 cancellation 完全无关。** asyncio 的 timeout 会借助 cancellation 停止内部等待，但对调用者呈现的是时间预算耗尽的语义。
- **误区：超时就应该自动重试。** 能否重试取决于业务操作是否适合重复执行以及错误类型。
- **误区：ExceptionGroup 只是把多个异常打印在一起。** 它让调用者能够保留并分类多个并行失败。
- **误区：optional dependency 失败一定要让整个请求失败。** 是否 required/optional 是业务规则。

## 本节规则总结

1. 远程调用应有明确的时间预算。
2. timeout、普通异常、caller cancellation 要区分。
3. required / optional 是业务语义。
4. `ExceptionGroup` 可以保留多个并行失败。
5. `except*` 用来按类型选择异常组中的匹配部分。
6. timeout 不自动意味着 retry。

## 关键问题

1. timeout 和 cancellation 的业务语义有何不同？
2. `asyncio.timeout()` 超时后，调用者通常看到什么？
3. 为什么并行 Task 可能需要 `ExceptionGroup`？
4. `except* ValueError` 在异常组上做了什么？
5. required 与 optional dependency 应由谁决定？
6. 为什么 timeout 不能自动等价于 retry？

## 场景命题

实现一个 required operation 的时间预算，并实现一个并行失败收集函数。两个 sibling 可能分别抛出不同类型的异常，不能只保留第一个失败。

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
