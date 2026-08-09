# Lesson 04 — Cancellation

## 本节目标

学完本节，你应该能够：

- 解释 `task.cancel()` 为什么是“请求取消”而不是强制杀死 Task
- 理解 `CancelledError` 的作用
- 正确让 cancellation 继续向外传播
- 用 `try/finally` 保证资源清理

## 进入本课前

你已经学过：Task、TaskGroup、Task owner，以及 Lesson 00 的 `finally`/cleanup。

上一课只把 cancel 暂时理解成“请求一个 Task 停止”；这一课正式学习它的执行语义。

## 为什么需要学习它

异步任务并不总是自然跑到结尾。调用者可能已经不需要结果，父业务操作可能失败，程序也可能正在结束。

**cancellation（取消）** 就是 asyncio 用来表达“这份异步工作现在应该停止”的控制流。

如果代码把取消当成普通错误随手吞掉，Task 可能继续做已经没有意义的工作，资源也可能无法按预期收尾。

## 核心理论

### 1. `task.cancel()` 做了什么

```python
task.cancel()
```

它不是立即终止线程，也不是把 Task 从内存里删除。

更准确地说，它会**向这个 Task 发出取消请求**。Task 需要继续被调度，并运行到能够响应取消的位置，才会真正观察到取消。

### 2. `CancelledError` 是什么

Task 响应取消时，异步代码会看到 `asyncio.CancelledError`。

可以把它理解成 asyncio 专门用来表示：

> “这次工作不是正常完成，也不是普通业务失败，而是上层要求停止。”

### 3. 为什么要让 cancellation 传播

这里的**传播（propagation）**就是“当前这一层观察到取消后，让调用它的上一层也继续知道这件事”。

```python
try:
    await do_work()
except asyncio.CancelledError:
    log_cancelled()
    raise
```

`raise` 会继续把取消向外传。

如果捕获 `CancelledError` 后直接返回一个正常值，上层就可能误以为工作成功完成。

### 4. cleanup 为什么放在 `finally`

Lesson 00 已经学过：`finally` 适合表达“无论怎样离开这里，都必须发生的收尾”。

```python
async def upload():
    resource = await open_resource()
    try:
        await send_chunks(resource)
    finally:
        await resource.close()
```

无论上传正常结束、发生异常，还是收到 cancellation，资源清理都处在同一个明确的位置。

### 5. cancellation 是合作式的

asyncio 不会在任意一条 Python 指令中间强制把 Task 杀掉。

如果一段代码长时间不 `await`、也没有其他可响应取消的点，那么 `cancel()` 发出以后，Task 可能还会继续运行一段时间。

这和前面学过的 Event Loop 合作式调度是一致的。

## 脑内执行模型

```text
Task upload: work ── await ........ CancelledError ── finally cleanup ── cancelled
caller:                         cancel() ───────────── await task ── 看见取消
```

## 常见误解

- **误区：`cancel()` 会立刻杀掉 Task。** 它发出取消请求，Task 需要获得执行机会才能响应。
- **误区：取消就是普通失败。** cancellation 表示“上层不再需要这份工作”，语义和业务异常不同。
- **误区：捕获 `CancelledError` 后返回默认值更友好。** 这会让上层误判操作成功。
- **误区：有 `except` 就不需要 `finally`。** `except` 用来处理特定异常，`finally` 更适合必须执行的资源清理。

## 本节规则总结

1. `cancel()` 是取消请求，不是强制终止。
2. Task 通过 `CancelledError` 观察取消。
3. cancellation 通常应该继续向调用者传播。
4. 必须执行的 cleanup 放进 `finally`。
5. 长时间不让出执行机会的代码也无法及时响应取消。

## 关键问题

1. 为什么调用 `cancel()` 后 Task 可能还没有立刻结束？
2. `CancelledError` 与普通业务异常表达的含义有什么不同？
3. 为什么捕获 `CancelledError` 后通常还要 `raise`？
4. 为什么 `finally` 适合放资源清理？
5. 如果一段 coroutine 很久都不 `await`，它对 cancellation 会有什么影响？

## 场景命题

实现分片上传：逐块等待发送。整个上传无论正常完成还是被取消，都必须执行 cleanup；被取消时不能伪装成成功。

## 验收

测试会在上传进行中调用 `cancel()`，确认 cleanup 恰好执行一次，并且等待该 Task 的调用者仍然能看到 `CancelledError`。

仓库参考实现：

```bash
uv run pytest lessons/04_cancellation/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/04_cancellation/tests -v --learner
```
