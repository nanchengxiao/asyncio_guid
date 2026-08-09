# Lesson 01 — Coroutine and await

## 本节目标

学完本节，你应该能够：

- 区分 coroutine function 与 coroutine object
- 判断 `foo()`、`await foo()` 何时执行函数体
- 理解 `await` 暂停的是当前 Task
- 区分数据依赖与可以并发的工作

## 为什么需要学习它

很多人会写 `await`，却不知道它暂停了谁。这个问题不解决，后面的 Task、Cancellation、Semaphore 都只剩 API 记忆。

## 核心理论

```python
async def fetch_user():
    print("start")
    return {"id": 1}

coro = fetch_user()   # 这里还没有打印
user = await coro      # 当前 Task 开始执行它
```

`async def` 定义 coroutine function；调用它得到 coroutine object。Coroutine object 是一份“可被执行的异步工作描述”，不是已经在后台运行的任务。

**Awaitable** 是“可以放在 `await` 右边的对象”的总称。Coroutine object 是 awaitable，Task 也是 awaitable；应用代码通常先掌握这两类即可，不需要过早深入手工 Future。

`await child()` 默认仍在**当前 Task** 内推进 child。它允许当前 Task 在 child 等待时把控制权交还 event loop，但不会自动创建第二个 Task。

## 脑内执行模型

```text
Task main
  build_order()
      │
      ├─ await fetch_order() ── wait... ── result
      │
      └─ await fetch_customer(order.customer_id)

只有一个 Task，所以数据依赖是清楚的；这里没有因为出现两个 await 就自动并发。
```

## 常见误解

- **误区：** 调用 async def 会立刻执行函数体。实际只创建 coroutine object。
- **误区：** 看到 await 就等于并发。单个 Task 连续 await 仍然可以完全串行。
- **误区：** await 会阻塞线程。它暂停当前 Task；事件循环线程可以运行其他 ready Task。
- **误区：** 所有 I/O 都应该立刻并发。存在数据依赖的调用必须等上游结果。

## 本节规则总结

1. 调用 coroutine function 得到 coroutine object。
2. coroutine object 只有被 await、包装成 Task 等之后才推进。
3. `await` 的直接语义是等待一个 awaitable，不是创建并发。
4. `await coroutine` 通常在当前 Task 中执行该 coroutine。
5. 先判断依赖，再讨论并发。

## 关键问题

1. `foo()`、`await foo()`、`create_task(foo())` 各自做了什么？
2. 为什么两个连续 await 可能完全没有并发？
3. 如果 B 的参数来自 A，B 能否与 A 同时开始？
4. await 一个已经完成的对象是否一定发生 Task 切换？
5. coroutine object 被创建但永远不 await，设计上意味着什么？

## 场景命题

一个订单上下文需要先获取 order，再用其中的 customer_id 获取 customer。请实现正确的数据依赖，并记录调用顺序。不要为了“异步”制造不存在的并发。

## 验收

测试验证 coroutine 创建不会触发业务调用，且 order 必须先于 customer 完成。

仓库参考实现：

```bash
uv run pytest lessons/01_coroutine_and_await/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/01_coroutine_and_await/tests -v --learner
```
