# Lesson 04 — Cancellation

## 本节目标

学完本节，你应该能够：

- 解释 `task.cancel()` 是取消请求而不是强制终止
- 正确传播 `CancelledError`
- 用 try/finally 保证 cleanup
- 识别吞掉 cancellation 的危险

## 为什么需要学习它

服务关闭、请求断开、父任务失败都会产生 cancellation。它不是罕见异常，而是异步系统的核心控制流。代码若把它吞掉，shutdown 就可能卡死或留下半完成资源。

## 核心理论

`task.cancel()` 会安排向目标 Task 注入 `CancelledError`。目标 Task 要运行到可响应取消的位置才能观察它。

```python
async def upload():
    resource = await open_resource()
    try:
        await send_chunks(resource)
    finally:
        await resource.close()
```

若需要记录取消，可以捕获后 `raise`；除非你非常明确地把取消转化为别的业务语义，否则不要假装成功返回。

## 脑内执行模型

```text
Task upload:  work ── await .......... CancelledError ── finally cleanup ── cancelled
caller:                              cancel() ─────────────── await task ── sees cancellation
```

## 常见误解

- **误区：** cancel() 会立即杀掉 Task。它是合作式取消请求。
- **误区：** `except Exception` 一定会捕获 CancelledError。现代 Python 中 CancelledError 继承 BaseException，且不应依赖大而泛的捕获处理取消。
- **误区：** cleanup 只要是同步代码就不会被取消。异步 cleanup 本身也可能遇到取消/异常，需要明确策略。
- **误区：** 取消后返回默认值更友好。这会欺骗上层，让它误判操作成功。

## 本节规则总结

1. 取消是控制流，不是罕见边缘情况。
2. `cancel()` 请求取消；目标 Task 在执行中观察 `CancelledError`。
3. 资源释放放进 finally。
4. 记录 cancellation 后通常重新抛出。
5. 父子任务的 cancellation propagation 应当事先设计。

## 关键问题

1. 调用 cancel 后为什么 Task 可能暂时还没结束？
2. 在哪些代码点 cancellation 最容易被观察到？
3. 为什么 finally 比 except 更适合资源清理？
4. 吞掉 CancelledError 会对 TaskGroup/shutdown 造成什么影响？
5. 异步 cleanup 如果也可能卡住，应增加什么边界？

## 场景命题

实现分片上传：逐块 await 发送，整个上传无论正常完成还是被取消都必须调用 cleanup；被取消时不能伪装成成功。

## 验收

测试在上传进行中 cancel Task，确认 cleanup 执行一次，且 await 该 Task 仍得到 CancelledError。

仓库参考实现：

```bash
uv run pytest lessons/04_cancellation/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/04_cancellation/tests -v --learner
```
