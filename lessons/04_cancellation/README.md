# Lesson 04 — 正确响应“停止这份工作”

## 进入本课前

你已经学过 Task、TaskGroup、owner、sibling Task，以及 Lesson 00 的 `finally` 和 cleanup。

## 本课新增术语

- **cancellation（取消）**：上层明确表示“这份 async 工作现在不需要继续了”的控制方式。
- **`task.cancel()`**：向某个 Task 发出 cancellation 请求的方法；它不是立即强制杀死 Task。
- **`CancelledError`**：Task 真正响应 cancellation 时看到的特殊异常。
- **cancellation propagation（取消传播）**：当前层收到 cancellation 后，不把它伪装成成功，而是让调用自己的上一层继续知道这份工作被取消。
- **cooperative cancellation（合作式取消）**：Task 需要自己运行到能够响应 cancellation 的位置，才能真正停下来；上层不会随时强行把它截断。
- **`raise`**：主动抛出异常；在 `except` 中单独写 `raise`，表示把刚捕获到的异常继续向外抛出。

## 本节目标

学完本节，你应该能够：

- 解释 `task.cancel()` 为什么只是请求；
- 理解 `CancelledError` 在 Task 中怎样出现；
- 正确进行 cancellation propagation；
- 用 `try/finally` 保证 cleanup；
- 解释为什么长时间不暂停的代码不能及时响应 cancellation。

## 为什么需要学习它

Async 工作并不总会自然跑到结尾。

调用者可能已经不再需要结果，父业务 operation 也可能已经失败。此时继续做无意义工作会浪费 resource；更严重的是，如果代码把 cancellation 当成普通成功吞掉，上层就会得到错误的业务判断。

## 核心理论

### 1. `cancel()` 发送请求，不是立即终止

```python
task.cancel()
```

这行代码表示：

> 希望这个 Task 尽快停止。

但调用 `cancel()` 的那一刻，Task 不一定已经结束。

Task 需要再次获得执行机会，并走到能够响应 cancellation 的位置，才会看到 `CancelledError`。

### 2. `await` 往往是 Task 能响应 cancellation 的位置

```python
async def upload():
    await send_chunk()
```

如果 `upload()` 正在等待 `send_chunk()`，上层发出 cancellation 后，Task 有机会在这段等待附近观察到 `CancelledError`。

如果一段普通 Python 代码一直计算、很久都没有暂停位置，它就无法及时响应 cancellation。

这就是 cooperative cancellation：

```text
上层发出 cancellation 请求
    ↓
Task 继续得到一次执行机会
    ↓
Task 在可响应位置看到 CancelledError
    ↓
执行自己的 cleanup
    ↓
结束
```

### 3. Cleanup 仍然应该放在 `finally`

```python
async def upload():
    resource = await open_resource()
    try:
        await send_chunks(resource)
    finally:
        await resource.close()
```

无论正常结束、普通异常，还是 cancellation，只要控制流离开这段 `try`，`finally` 都负责收尾。

### 4. 捕获 `CancelledError` 后通常还要继续向外 propagation

如果只是为了记录：

```python
try:
    await do_work()
except asyncio.CancelledError:
    log_cancelled()
    raise
```

这里单独写 `raise` 很重要：它让同一个 cancellation 继续向调用者传播。

如果改成：

```python
except asyncio.CancelledError:
    return "ok"
```

上层可能误以为工作成功完成。

### 5. Cancellation 与普通业务失败表达不同意思

```text
普通异常     → 工作尝试了，但发生失败
cancellation → 上层决定这份工作不需要继续
```

两者都可能经过异常机制，但业务含义不同，所以不要把 cancellation 随手塞进普通错误处理里。

## 脑内执行模型

```text
Task：   工作 ─ await .... CancelledError ─ finally cleanup ─ 结束
调用者：              cancel() ───────────── await Task ─ 看见 cancellation
```

关键顺序：

1. 调用者调用 `cancel()`；
2. Task 之后才真正观察到 `CancelledError`；
3. Task 先执行 `finally` cleanup；
4. 调用者等待 Task 时继续看见 cancellation。

## 常见误解

- **误区：** `cancel()` 会立即杀掉 Task。  
  **更准确：** 它只发送 cancellation 请求。

- **误区：** cancellation 与普通业务异常完全一样。  
  **更准确：** cancellation 表达的是“上层不再需要继续工作”。

- **误区：** 捕获 `CancelledError` 后返回默认值更友好。  
  **更准确：** 这可能把 cancellation 错误伪装成成功。

- **误区：** 有 `except` 就不需要 `finally`。  
  **更准确：** 必须执行的 resource cleanup 仍然更适合放在 `finally`。

- **误区：** cancellation 一定立即生效。  
  **更准确：** cooperative cancellation 依赖 Task 运行到可响应位置。

## 本节规则总结

1. `cancel()` 是 cancellation 请求，不是强制终止。
2. Task 通过 `CancelledError` 观察 cancellation。
3. Cancellation 通常应该继续向调用者 propagation。
4. `raise` 可以让已经捕获的 cancellation 继续向外传播。
5. Cleanup 放在 `finally`。
6. 长时间不暂停的代码无法及时响应 cooperative cancellation。
7. 不要把 cancellation 伪装成普通成功。

## 关键问题

1. 为什么调用 `cancel()` 后 Task 可能还没结束？
2. `CancelledError` 在什么时机可能被 Task 观察到？
3. cooperative cancellation 为什么需要 Task 自己配合？
4. cancellation 与普通业务异常的含义有什么不同？
5. 为什么捕获 `CancelledError` 后通常还要 `raise`？
6. 为什么 `finally` 适合放 resource cleanup？
7. 很久都不暂停的代码会怎样影响 cancellation？

## 场景命题

实现分片上传：逐块等待发送。

无论正常完成还是收到 cancellation，都必须执行 cleanup；如果上传被取消，不能把结果伪装成“成功完成”。

## 验收

测试会在上传进行中调用 `cancel()`，并确认：

- cleanup 恰好执行一次；
- Task 最终停止；
- 调用者仍然能看到 `CancelledError`；
- cancellation 没有被转换成普通成功。

仓库参考实现：

```bash
uv run pytest lessons/04_cancellation/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/04_cancellation/tests -v --learner
```
