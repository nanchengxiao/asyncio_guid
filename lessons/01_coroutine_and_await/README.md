# Lesson 01 — Coroutine and await

## 本节目标

学完本节，你应该能够：

- 区分 coroutine function 与 coroutine object
- 判断 `foo()`、`await foo()` 何时真正执行函数体
- 理解 `await` 的基本含义
- 区分数据依赖与可以考虑并发的工作

## 进入本课前

你已经从 Lesson 00 学过 generator 的“暂停/恢复”直觉，以及 `yield` 的基本作用。

**仍然不要求你知道 Task 或 Event Loop。** 它们是下一课的主题。

## 为什么需要学习它

很多人看到 `async def` 就以为函数已经“异步运行起来了”，看到 `await` 就以为“发生了并发”。这一课只解决最基础的问题：**异步函数被调用后得到什么，代码又在什么时候真正执行。**

## 核心理论

先认识三个词：

- **coroutine（协程）**：一种可以在执行途中暂停、之后从原位置继续的异步执行过程。
- **coroutine function（协程函数）**：用 `async def` 定义的函数。
- **coroutine object（协程对象）**：调用 coroutine function 后得到的对象；创建它不等于已经开始后台执行。

```python
async def fetch_user():
    print("start")
    return {"id": 1}

coro = fetch_user()   # 这里只创建 coroutine object，还不会打印 start
user = await coro      # 到这里才真正推进这份异步工作
```

`await` 可以先理解为：

> **等待右边的异步工作得到结果；如果结果暂时没有准备好，当前 coroutine 可以暂停，之后再继续。**

**Awaitable（可等待对象）** 是“可以写在 `await` 右边的对象”的总称。coroutine object 就是一种 Awaitable；下一课会学到的 Task 也是。

`await` 本身不等于并发。例如：

```python
order = await fetch_order(order_id)
customer = await fetch_customer(order["customer_id"])
```

第二步需要第一步返回的 `customer_id`，这叫**数据依赖**。后一步缺少前一步结果就无法开始，所以这里按顺序执行是正确的。

## 脑内执行模型

```text
调用 fetch_order(...)
      ↓
得到 coroutine object
      ↓
await 它，真正执行
      ↓
拿到 order
      ↓
再创建并 await fetch_customer(...)
```

这一课先关心“创建”和“真正执行”的区别；暂停后如何安排其他工作，下一课再讲。

## 常见误解

- **误区：** 调用 `async def` 会立刻执行函数体。实际通常只是创建 coroutine object。
- **误区：** `await` 就等于并发。它首先表示“等待一个 Awaitable”。
- **误区：** 异步代码就应该把所有网络请求、数据库查询一起开始。存在数据依赖时必须尊重依赖。
- **误区：** coroutine object 已经在后台运行。它只是待执行的异步工作对象。

## 本节规则总结

1. `async def` 定义 coroutine function。
2. 调用它得到 coroutine object，通常不会立刻执行函数体。
3. coroutine object 是 Awaitable，可以被 `await`。
4. `await` 表示等待，不表示自动创建并发。
5. 先判断数据依赖，再讨论并发。

## 关键问题

1. `async def foo()` 定义出来的 `foo` 是什么？
2. `foo()` 返回什么？为什么这时函数体通常还没执行？
3. `await foo()` 做了什么？
4. Awaitable 是什么？
5. 如果 B 的参数来自 A 的返回结果，B 能否与 A 同时开始？

## 场景命题

一个订单上下文需要先获取 order，再用其中的 `customer_id` 获取 customer。请保持真实的数据依赖，不要为了“异步”制造不存在的并发。

## 验收

测试会验证：创建 coroutine 不会提前触发业务调用，并且 customer 查询只能在 order 返回之后开始。

仓库参考实现：

```bash
uv run pytest lessons/01_coroutine_and_await/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/01_coroutine_and_await/tests -v --learner
```
