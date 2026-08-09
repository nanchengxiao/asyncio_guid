# Lesson 01 — Coroutine and await

## 本节目标

学完本节，你应该能够：

- 区分 coroutine function 与 coroutine object
- 判断 `foo()`、`await foo()` 何时真正执行函数体
- 理解 `await` 为什么可以让一段异步工作暂停并稍后继续
- 区分“存在数据依赖”与“可以考虑并发”的工作

## 进入本课前

你已经从 Lesson 00 学过：

- generator 可以暂停并从原处恢复；
- `yield` 会产出值并暂停；
- `finally` 与资源生命周期的基本作用。

**仍然不要求你知道 Task 或 Event Loop。** 它们是下一课的主题。

## 为什么需要学习它

`asyncio` 最容易产生的第一个误解是：看到 `async def` 就以为函数已经“异步运行起来了”，看到 `await` 就以为“发生了并发”。

这一课只解决最基础的问题：**异步函数被调用以后到底得到了什么，代码又在什么时候真正开始执行。**

## 核心理论

### 1. coroutine 是什么

**coroutine（协程）** 可以先理解成：

> 一种能够在执行途中暂停，等条件满足后再从原位置继续的函数执行过程。

它和上一课 generator 的“暂停/恢复”直觉相似，但协议不同：generator 主要围绕 `yield` 产出数据；asyncio coroutine 主要围绕 `await` 等待异步工作。

### 2. coroutine function 与 coroutine object

```python
async def fetch_user():
    print("start")
    return {"id": 1}
```

用 `async def` 定义出来的 `fetch_user` 是 **coroutine function（协程函数）**。

调用它：

```python
coro = fetch_user()
```

这一步通常**不会执行函数体**，所以还不会打印 `start`。得到的 `coro` 是 **coroutine object（协程对象）**。

可以把它理解成：

```text
coroutine function
      │ 调用
      ▼
coroutine object
      │ 之后被真正推进
      ▼
函数体开始执行
```

coroutine object 描述了一份“可以执行的异步工作”，但创建它不等于这份工作已经在后台运行。

### 3. `await` 是什么

`await` 的意思可以先理解为：

> **等待右边的异步工作得到结果；如果现在还不能得到结果，当前 coroutine 可以暂停，之后再继续。**

```python
coro = fetch_user()
user = await coro
```

执行到 `await coro` 时，`fetch_user` 才会被真正推进，因此会打印 `start` 并返回结果。

Lesson 00 中 generator 用 `yield` 暂停；这里 coroutine 常在 `await` 处出现暂停机会。至于“暂停以后是谁去运行别的工作”，下一课再解释 Event Loop 与 Task。

### 4. Awaitable 是什么

**Awaitable（可等待对象）** 是一个总称：

> 可以写在 `await` 右边的对象。

coroutine object 就是一种 awaitable。下一课会学到 Task，Task 也是 awaitable。

现阶段只需要记住：

```python
result = await something
```

要求 `something` 是 awaitable。

### 5. `await` 不等于并发

```python
order = await fetch_order(order_id)
customer = await fetch_customer(order["customer_id"])
```

第二步需要第一步返回的 `customer_id`，这叫**数据依赖**：后一步缺少前一步的结果就无法正确开始。

所以这里连续两个 `await` 完全合理，而且本质上是按依赖顺序执行。

不要因为“学的是 asyncio”，就强行把所有调用同时开始。

## 脑内执行模型

```text
调用 fetch_order(...)
      ↓
得到 coroutine object
      ↓
await 它
      ↓
fetch_order 真正执行并返回 order
      ↓
拿到 order["customer_id"]
      ↓
再创建并 await fetch_customer(...)
```

这一课先关心“创建”和“真正执行”的区别，不要求你分析调度器。

## 常见误解

- **误区：调用 `async def` 会立刻执行函数体。** 实际上通常只是创建 coroutine object。
- **误区：`await` 就等于并发。** `await` 的直接作用是等待一个 awaitable；是否存在并发，要到下一课结合 Task 才能判断。
- **误区：异步代码就应该把所有网络请求、数据库查询等等待型调用一起开始。** 如果后一步依赖前一步结果，就必须尊重依赖。
- **误区：coroutine object 已经在后台运行。** 它只是待执行的异步工作对象。

## 本节规则总结

1. `async def` 定义 coroutine function。
2. 调用 coroutine function 得到 coroutine object，通常不会立刻执行函数体。
3. coroutine object 是 awaitable，可以被 `await`。
4. `await` 表达“等待结果，并允许当前 coroutine 在需要时暂停”，不是“自动并发”。
5. 先判断数据依赖，再讨论是否应该并发。

## 关键问题

1. `async def foo()` 定义出来的 `foo` 是什么？
2. `foo()` 返回什么？为什么这时函数体通常还没执行？
3. `await foo()` 做了什么？
4. Awaitable 是什么？coroutine object 为什么属于 Awaitable？
5. 如果 B 的参数来自 A 的返回结果，为什么不能为了“异步”强行让 A、B 同时开始？
6. coroutine object 被创建后永远没有被等待，意味着什么？

## 场景命题

一个订单上下文需要先获取 order，再用其中的 `customer_id` 获取 customer。请实现真实的数据依赖，并记录调用顺序。不要为了“异步”制造不存在的并发。

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
