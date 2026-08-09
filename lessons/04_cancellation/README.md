# Lesson 04 — Cancellation

## 本节目标

学完本节，你应该能够：

- 解释 `task.cancel()` 是取消请求而不是强制终止
- 理解 `CancelledError`
- 正确传播 cancellation
- 用 `try/finally` 保证 cleanup

## 进入本课前

你已经学过 Task、TaskGroup、Task owner，以及 Lesson 00 的 `finally` / cleanup。

本课新增：

- **cancellation（取消）**：上层表示“这份异步工作现在应该停止”的控制方式。
- **`CancelledError`**：Task 响应取消时看到的特殊异常。
- **传播（propagation）**：当前层看到取消后，让调用它的上一层也继续知道这件事。

## 为什么需要学习它

异步任务并不总会自然跑到结尾：调用者可能已经不需要结果，父业务操作也可能失败。如果代码把取消吞掉，Task 可能继续做已经没有意义的工作，资源也可能无法正确收尾。

## 核心理论

```python
task.cancel()
```

这不会立即“杀死” Task，而是向它发出取消请求。Task 需要再次获得执行机会，并运行到能够响应取消的位置，才会观察到 `CancelledError`。

```python
async def upload():
    resource = await open_resource()
    try:
        await send_chunks(resource)
    finally:
        await resource.close()
```

如果只是为了记录取消，可以捕获后继续 `raise`：

```python
try:
    await do_work()
except asyncio.CancelledError:
    log_cancelled()
    raise
```

否则上层可能误以为工作正常成功。

取消是合作式的：如果一段代码长时间不 `await`、不让出执行机会，它也无法及时响应 `cancel()`。

## 脑内执行模型

```text
Task:   work ─ await .... CancelledError ─ finally cleanup ─ cancelled
caller:              cancel() ───────────── await task ─ 看见取消
```

## 常见误解

- **误区：** `cancel()` 会立即杀掉 Task。它只是发出取消请求。
- **误区：** cancellation 和普通业务异常完全一样。取消表达的是“上层不再需要这份工作”。
- **误区：** 捕获 `CancelledError` 后返回默认值更友好。这会让上层误判成功。
- **误区：** 有 `except` 就不需要 `finally`。必须执行的资源清理仍更适合放在 `finally`。

## 本节规则总结

1. `cancel()` 是请求，不是强制终止。
2. Task 通过 `CancelledError` 观察取消。
3. cancellation 通常应该继续向调用者传播。
4. cleanup 放在 `finally`。
5. 长时间不让出的代码无法及时响应取消。

## 关键问题

1. 为什么调用 `cancel()` 后 Task 可能还没结束？
2. `CancelledError` 与普通业务异常表达的含义有什么不同？
3. 为什么捕获 `CancelledError` 后通常还要 `raise`？
4. 为什么 `finally` 适合放资源清理？
5. 很久都不 `await` 的代码会怎样影响取消？

## 场景命题

实现分片上传：逐块等待发送。无论正常完成还是被取消都必须执行 cleanup；取消不能被伪装成成功。

## 验收

测试会在上传进行中调用 `cancel()`，确认 cleanup 恰好执行一次，并且调用者仍然能看到 `CancelledError`。

仓库参考实现：

```bash
uv run pytest lessons/04_cancellation/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/04_cancellation/tests -v --learner
```
