# Lesson 05 — 给等待设时限并区分失败结果

## 进入本课前

你已经学过 TaskGroup、sibling Task、cancellation、`CancelledError` 和 cancellation propagation。

## 本课新增术语

- **operation（一次业务操作）**：为了完成一个业务目标而执行的一段完整工作，例如“获取订单详情”。
- **timeout（超时）**：等待超过允许时间后，不再继续等下去。
- **time budget（时间预算）**：某段 operation 最多允许占用的等待时间。
- **`asyncio.timeout()`**：给一个缩进代码块设置 time budget 的 asyncio 工具。
- **`TimeoutError`**：表示 time budget 已经耗尽、调用者不能再继续等待的异常。
- **required dependency（必需依赖）**：它失败后，当前业务结果就不能成立的依赖。
- **optional dependency（可选依赖）**：它失败后，当前业务仍可以返回一个缺少部分内容但仍可用的结果。
- **degradation（降级）**：某个 optional dependency 失败时，主动返回功能较少但仍可用的结果，而不是让整个业务失败。
- **`ExceptionGroup`**：一个可以同时携带多个异常的异常对象。
- **`except*`**：从 `ExceptionGroup` 中按异常类型选择并处理匹配部分的语法。
- **retry（重试）**：一次 operation 失败后，再发起一次新的尝试。

## 本节目标

学完本节，你应该能够：

- 使用 `asyncio.timeout()` 建立 time budget；
- 区分 timeout 与 cancellation 的业务含义；
- 理解 `TimeoutError`、`ExceptionGroup` 与 `except*`；
- 区分 required dependency 与 optional dependency；
- 解释 degradation 与 retry 为什么都必须服从业务规则。

## 为什么需要学习它

真实 operation 不只有“成功”和“失败”两种结果。

同一次业务调用可能：

- 成功返回；
- 发生普通异常；
- 等待时间耗尽；
- 被上层要求停止。

如果这些结果全部混成一个“错误”，后续就无法正确决定：整个业务该失败、该 degradation，还是值得 retry。

## 核心理论

### 1. 用 `asyncio.timeout()` 给一段等待设 time budget

```python
async with asyncio.timeout(0.5):
    result = await external_call()
```

这里表示：这段 operation 最多允许等待约 0.5 秒。

如果时间耗尽，这个代码块内部会借助前一课学过的 cancellation 停止继续等待；离开 `asyncio.timeout()` 的边界后，调用者通常看到 `TimeoutError`。

所以可以这样区分：

```text
cancellation → 上层决定这份工作不再需要继续
timeout      → 这份工作已经等得太久，time budget 用完
```

### 2. Timeout 不是普通失败的另一个名字

一次外部调用的几种结果应该分开：

```text
成功             → 得到正常值
普通异常         → 工作本身失败
timeout          → 等待时间耗尽
cancellation     → 上层不再需要继续
```

它们可能最终都经过异常控制流，但业务含义不同。

### 3. Required 与 optional 是业务规则

例如：

```text
订单主数据：required
推荐数据：optional
```

如果订单主数据失败，页面无法成立；如果推荐数据失败，页面可能仍能返回，只是缺少推荐内容。

这种“缺少可选内容但仍返回”的处理，就是 degradation。

不要把 optional 理解成：

```python
try:
    ...
except Exception:
    pass
```

Optional 只说明“业务允许缺少这部分结果”，并不意味着可以吞掉所有异常，更不能顺手吞掉 cancellation。

### 4. Concurrency 的 sibling 可能在相近时间分别失败

假设同一个 `TaskGroup` 中有多个 sibling Task，它们在很接近的时间分别失败。

Python 可以用 `ExceptionGroup` 把多个异常一起保留下来，而不是只丢出第一个。

```python
try:
    async with asyncio.TaskGroup() as tg:
        ...
except* ValueError as group:
    ...
```

`except* ValueError` 会从异常组中挑出匹配 `ValueError` 的那部分。

它不是“拿第一个异常”，而是在一组异常里做类型匹配。

### 5. Timeout 不自动等于 retry

Retry 的基础含义很简单：失败后再试一次。

但能不能 retry 需要另外判断：

- 失败是否可能只是暂时的；
- 重复执行是否安全；
- retry 会不会给已经处理不过来的外部系统增加更多压力。

这些更完整的约束会在最后一课组合起来；本课只先建立规则：

> timeout 只说明“不能继续等”，不自动说明“应该再试一次”。

## 脑内执行模型

```text
operation
  ├─ 成功             → 正常值
  ├─ 普通异常         → 普通失败
  ├─ timeout          → time budget 耗尽
  └─ cancellation     → 上层不再需要继续
```

对于 dependency：

```text
required 依赖失败 → 当前业务整体不能成立
optional 依赖失败 → 可以选择 degradation
```

## 常见误解

- **误区：** timeout 与 cancellation 完全无关。  
  **更准确：** `asyncio.timeout()` 内部会借助 cancellation 停止等待，但对调用者表达的是 time budget 耗尽。

- **误区：** 超时就一定应该 retry。  
  **更准确：** retry 需要单独判断失败类型和重复执行是否安全。

- **误区：** `ExceptionGroup` 只需要打印。  
  **更准确：** 它让多个 concurrency failure 可以被同时保留和分类。

- **误区：** optional dependency 失败必须让整个 operation 失败。  
  **更准确：** required / optional 是业务规则。

- **误区：** optional 就等于吞掉异常。  
  **更准确：** degradation 也必须明确哪些失败可以被隔离。

## 本节规则总结

1. 外部 operation 应有明确 time budget。
2. Timeout、普通异常和 cancellation 要区分。
3. Required / optional dependency 由业务决定。
4. Degradation 只用于业务允许缺少的 optional 结果。
5. `ExceptionGroup` 可以保留多个 concurrency failure。
6. `except*` 用于按异常类型处理 `ExceptionGroup`。
7. Timeout 不自动等于 retry。

## 关键问题

1. operation 在本课里是什么意思？
2. time budget 与 timeout 分别是什么？
3. `asyncio.timeout()` 负责什么？
4. `asyncio.timeout()` 超时后调用者通常看到什么？
5. timeout 与 cancellation 的业务含义有什么不同？
6. required dependency 与 optional dependency 应由谁决定？
7. degradation 是什么？
8. 为什么多个 Task 可能需要 `ExceptionGroup`？
9. `except* ValueError` 做了什么？
10. 为什么 timeout 不能自动等价于 retry？

## 场景命题

实现一个 required operation 的 time budget，并实现一个同时保留多份错误的函数。

要求：

- operation 超过 time budget 后停止等待；
- required 依赖失败继续向外报告；
- 多个 sibling Task 失败时不能只保留第一个异常。

## 验收

测试会验证：

- timeout 边界生效；
- required 依赖失败没有被错误 degradation；
- 多个同时发生的失败没有被错误丢失；
- cancellation 与普通 timeout 没有被混成同一个结果。

仓库参考实现：

```bash
uv run pytest lessons/05_timeout_and_errors/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/05_timeout_and_errors/tests -v --learner
```
