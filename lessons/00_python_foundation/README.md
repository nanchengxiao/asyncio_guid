# Lesson 00 — Python foundation

## 本节目标

学完本节，你应该能够：

- 解释 iterator / generator 为什么能够暂停并恢复
- 用 context manager 表达资源生命周期
- 说明 `finally` 为什么是异步 cleanup 的前置模型
- 预测提前退出时清理代码是否执行

## 为什么需要学习它

asyncio 的取消、异步上下文管理和 worker shutdown 都依赖同一个基础事实：代码会在中途结束，但资源仍然必须被可靠释放。若 `finally` 和上下文管理器不牢，后面的 cancellation 会变成机械背诵。

## 核心理论

先区分两个词：**iterable** 是“可以开始一次迭代”的对象；**iterator** 是“已经处在某次迭代过程中、记得当前位置”的对象。`iter(iterable)` 得到 iterator，`next(iterator)` 推进一步。

Generator 是一种特别方便的 iterator。调用生成器函数不会把整个函数跑完；每次 `next()` 执行到 `yield` 暂停，并保存局部状态。

```python
def batches():
    yield [1, 2]
    yield [3, 4]
```

这和 coroutine 的“可暂停、可恢复”不是同一个协议，但给我们提供了相似的执行直觉。

再看资源：

```python
resource = open_resource()
try:
    use(resource)
finally:
    resource.close()
```

`try / except / finally` 分工不同：`except` 处理你决定要处理的失败，`finally` 则负责无论成功、失败还是提前退出都必须发生的收尾。`with` / context manager 把 acquire/use/release 固定在同一个可见代码块。

`finally` 表达的不是“成功后的收尾”，而是“离开这个生命周期边界时必须做的事”。这会直接迁移到后面的 cancellation cleanup。

## 脑内执行模型

```text
进入资源 ──→ 读取第 1 批 ──→ 读取第 2 批 ──→ 提前 break
   │                                      │
   └──────────── finally / __exit__ ◀─────┘
```

脑中要同时保存两件事：数据迭代到哪，以及谁负责关闭资源。

## 常见误解

- **误区：** generator function 一调用就会执行到第一个 yield。实际是只创建 generator object。
- **误区：** 只有抛异常时 finally 才运行。正常 return、break 或异常展开都会进入 finally。
- **误区：** context manager 只是语法糖，所以资源是否关闭不重要。语法糖恰恰是在编码生命周期约束。

## 本节规则总结

1. 可暂停对象必须保存恢复位置与局部状态。
2. 资源 acquire 与 release 应放在同一个可见生命周期边界。
3. cleanup 放进 finally，而不是依赖调用者记得手工执行。
4. 提前结束和异常是资源设计的正常路径。

## 关键问题

1. 生成器函数调用和 `next()` 的执行语义分别是什么？
2. 一个 consumer 在第二个元素后 break，generator 的 finally 何时执行？
3. 为什么资源生命周期比“记得调用 close”更可靠？
4. 这个模型怎样为 cancellation 做准备？
5. 如果 cleanup 本身失败，调用者应该看到什么？

## 场景命题

实现一个 `managed_records` 上下文管理器。它暴露惰性记录流；consumer 可以只读前几个元素就停止，但资源必须关闭。不要把全部记录提前读入内存。

## 验收

测试检查惰性迭代顺序，以及正常结束和提前结束时 cleanup 都被执行。

仓库参考实现：

```bash
uv run pytest lessons/00_python_foundation/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/00_python_foundation/tests -v --learner
```
