# Lesson 02 — Event Loop and Task

## 本节目标

学完本节，你应该能够：

- 用自己的话解释 Event Loop 和 Task 分别负责什么
- 解释 Coroutine → Task → Event Loop 的关系
- 说明真正的 asyncio 并发为什么来自多个同时存活的 Task
- 预测 `create_task()` 后的基本执行时间线
- 识别可以并发的独立 I/O

## 进入本课前

你已经从 Lesson 01 学过：

- coroutine function 与 coroutine object；
- Awaitable；
- `await` 会等待结果，并可能让当前 coroutine 暂停；
- 数据依赖必须按顺序满足。

这一课第一次正式引入 **Event Loop、Task、并发和调度**。

## 为什么需要学习它

前一课只知道“一段 coroutine 可以暂停”，还没有回答一个关键问题：

> 它暂停以后，程序为什么还能去做别的事情？

答案就是 Event Loop 和 Task。

## 核心理论

### 1. Event Loop 是什么

**Event Loop（事件循环）** 可以先理解成 asyncio 的调度中心：

> 它不断查看“哪些异步工作现在可以继续”，然后让这些工作轮流向前执行。

它通常运行在一个线程里。某段 Python 代码正在执行时，Event Loop 不会强行把它抢走；正在运行的异步工作需要在合适的位置主动让出执行机会，例如等待尚未完成的 I/O。

### 2. Task 是什么

Lesson 01 的 coroutine object 只是“待执行的异步工作”。

**Task（任务）** 则可以理解成：

> 被 Event Loop 正式登记、拥有独立执行进度的一份 coroutine 工作。

```python
user_task = asyncio.create_task(fetch_user())
```

`create_task()` 会把 coroutine 包装成 Task，并登记给正在运行的 Event Loop。

可以先记住这条关系：

```text
coroutine object
      ↓ create_task(...)
Task
      ↓ 由它调度
Event Loop
```

### 3. 什么叫“调度”

**调度（scheduling）** 就是“决定接下来让哪一份可以继续的工作向前执行”。

asyncio 的调度是合作式的：一份 Task 如果一直执行普通 Python 代码、不主动等待或让出，其他 Task 就没有机会运行。

### 4. 什么叫“并发”

这里的**并发（concurrency）**不是“两个 Python 语句在同一瞬间由两个 CPU 同时执行”。

在本课程的 asyncio 语境里，它主要表示：

> 多份工作在同一段时间内都处于进行状态；其中一份等待 I/O 时，另一份可以继续推进，因此等待时间能够重叠。

I/O（Input/Output，输入/输出）可以是网络请求、数据库查询、文件读取等。这类工作常常花时间“等待外部结果”。

### 5. 两个 Task 为什么能比两个连续 await 更快

串行写法：

```python
user = await fetch_user()
orders = await fetch_orders()
```

第二个调用要等第一个完全结束才开始。

如果它们互不依赖，可以先创建两个 Task：

```python
user_task = asyncio.create_task(fetch_user())
orders_task = asyncio.create_task(fetch_orders())

user = await user_task
orders = await orders_task
```

此时两个 Task 都已经存在。只要其中一个进入等待，Event Loop 就有机会推进另一个。

如果两个请求各等待约 100ms，总时间可能接近 100ms，而不是约 200ms。

### 6. `create_task()` 不会“立刻抢占”当前代码

```python
task = asyncio.create_task(fetch_user())
print("after create")
```

新 Task 已经被登记，但这不意味着它会在 `create_task()` 返回前强行插入执行。

当前正在执行的 Task 还会继续，直到它到达一个让出执行机会的位置。之后 Event Loop 才能选择其他 Task。

### 7. `asyncio.run()` 是什么

应用程序通常从同步世界进入 asyncio：

```python
async def main():
    ...

asyncio.run(main())
```

对应用层代码，可以先把 `asyncio.run(main())` 理解为：

1. 创建并运行 Event Loop；
2. 让 `main()` 这份异步工作运行到结束；
3. 做必要的收尾并关闭 Event Loop。

一般不需要为每个业务函数手工创建 Event Loop。

## 脑内执行模型

```text
当前 Task: create user ─ create orders ─ await user ........ await orders
                             │              │
user Task:                    └─ start ─ wait I/O ........ finish
orders Task:                       └─ start ─ wait I/O ........ finish

                         时间 →
```

关键不是代码里有几个 `await`，而是**同一时间是否存在多个能够独立推进的 Task**。

## 常见误解

- **误区：Task 就是线程。** Task 是 asyncio 的异步工作单位，多个 Task 通常仍在同一个 Event Loop 线程中合作式运行。
- **误区：`create_task()` 一调用，新 Task 就会立刻抢占当前代码。** 当前工作要先让出执行机会。
- **误区：两个连续 `await` 就是并发。** 如果第二个 await 直到第一个结束后才创建，通常仍是串行。
- **误区：并发越多一定越快。** 资源有容量上限；后面的课程会专门处理并发限制。
- **误区：Event Loop 可以自动打断长时间计算。** 它不能强行抢占一直运行的普通 Python 代码。

## 本节规则总结

1. Event Loop 是 asyncio 的调度中心。
2. Task 是被 Event Loop 调度、拥有自己执行进度的 coroutine 工作。
3. `create_task()` 把 coroutine 变成可独立推进的 Task。
4. asyncio 并发主要通过让多个 Task 的等待时间重叠获得收益。
5. 只有彼此无数据依赖、并发有收益的工作才应该同时开始。

## 关键问题

1. coroutine object 与 Task 最大的区别是什么？
2. Event Loop 的核心职责是什么？
3. 为什么 `await fetch_user(); await fetch_orders()` 通常是串行？
4. `create_task()` 后，新 Task 最早什么时候有机会运行？
5. 为什么 Event Loop 不能解决一个长时间不让出的纯 Python 计算？
6. 从时间线看，怎样判断两个 I/O 的等待是否真正重叠？

## 场景命题

Dashboard 同时需要 user 与 orders。它们只依赖同一个 `user_id`，彼此没有数据依赖。

把不必要的串行等待改成真正并发，并确保函数返回时它自己创建的工作已经结束。

## 验收

测试会给两个 I/O 设置可控延迟，验证结果正确，并确认总时间明显短于串行执行时的等待时间之和。

仓库参考实现：

```bash
uv run pytest lessons/02_event_loop_and_task/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/02_event_loop_and_task/tests -v --learner
```
