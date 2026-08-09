# Lesson 05 — Timeout and errors

## 本节目标

学完本节，你应该能够：

- 使用 `asyncio.timeout()` 建立时间预算
- 区分 timeout 与 cancellation 的业务语义
- 理解 TaskGroup 的 ExceptionGroup
- 使用 `except*` 对并行失败分类

## 为什么需要学习它

真实服务调用不只有“成功/失败”。同一个 operation 可能成功、业务异常、超时或被上层取消。若这些语义不明确，重试、降级和告警都会混在一起。

## 核心理论

`asyncio.timeout()` 把一个作用域限制在时间预算内。超时时，作用域内部通过 cancellation 停止正在进行的等待，调用者在边界外看到 `TimeoutError`。

并行兄弟任务可能在接近的时间失败，TaskGroup 会用 `ExceptionGroup` 表达“多个失败同时存在”。

```python
try:
    async with asyncio.TaskGroup() as tg:
        ...
except* ValueError as group:
    ...
```

`except*` 不是“把第一个异常拿出来”，而是按类型从异常树中选择匹配子组。

## 脑内执行模型

```text
operation
  ├─ success → value
  ├─ exception → domain/system error
  ├─ timeout → budget exhausted
  └─ cancellation → caller no longer wants work
```

## 常见误解

- **误区：** timeout 就是普通异常，与 cancellation 无关。asyncio timeout 内部通过取消当前工作来实现时间边界。
- **误区：** 超时后所有异常都应该重试。是否重试取决于幂等性和错误类型。
- **误区：** ExceptionGroup 只需要打印。并行失败常需要按类型分别记录/处理。
- **误区：** optional dependency 失败应该让整个请求失败。是否 required 是业务语义，不是 asyncio 决定的。

## 本节规则总结

1. 每个远程调用都应有明确的时间预算来源。
2. timeout、caller cancellation、domain failure 要区分。
3. TaskGroup 可以传播多个并行失败。
4. `except*` 用于异常组的类型化选择。
5. required/optional 决策先于 API 选择。

## 关键问题

1. asyncio.timeout 超时后调用者通常看到什么？
2. timeout 为什么不应自动等价于 retry？
3. TaskGroup 为什么需要 ExceptionGroup 而不是只抛第一个异常？
4. optional 下游超时和 required 下游超时应有何不同？
5. except* 与普通 except 在 ExceptionGroup 上的语义差异是什么？

## 场景命题

实现一个有总时间预算的 required 调用，并实现一个并行失败分类函数：两个 sibling 可能分别抛 ValueError / RuntimeError，需要用 ExceptionGroup 语义保留并分类。

## 验收

测试 timeout 边界、required 失败传播，以及多个并行失败没有被错误丢失。

仓库参考实现：

```bash
uv run pytest lessons/05_timeout_and_errors/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/05_timeout_and_errors/tests -v --learner
```
