# Lesson 02 — Event Loop and Task

## 本节目标

学完本节，你应该能够：

- 解释 Event Loop 和 Task 分别负责什么
- 说明并发为什么来自多个同时存活的 Task
- 预测 `create_task()` 后的基本执行时间线
- 识别可以并发的独立 I/O

## 进入本课前

你已经学过 coroutine、Awaitable、`await`，以及“数据依赖必须按顺序满足”。

这一课第一次正式引入 **Event Loop、Task、调度和并发**。

## 为什么需要学习它

前一课知道 coroutine 可以暂停，但还没有回答：**它暂停以后，程序为什么还能去做别的事情？** 这就是 Event Loop 和 Task 要解决的问题。

## 核心理论

先认识几个词：

- **Event Loop（事件循环）**：asyncio 的调度中心，负责让当前可以继续的异步工作轮流向前执行。
- **Task（任务）**：被 Event Loop 正式登记、拥有自己执行进度的一份 coroutine 工作。
- **调度（scheduling）**：决定接下来让哪一个可以继续的 Task 向前执行。
- **并发（concurrency）**：多份工作在同一段时间内都处于进行状态；一份工作等待时，另一份可以推进。
- **I/O（Input/Output）**：网络、数据库、文件等输入/输出操作，通常包含等待外部结果的时间。

Event Loop 通常运行在一个 **thread（线程）** 中。这里先把线程理解成“程序的一条执行路径”即可，本课不展开多线程。

```python
user_task = asyncio.create_task(fetch_user())
orders_task = asyncio.create_task(fetch_orders())

user = await user_task
orders = await orders_task
```

`create_task()` 会把 coroutine 包装成 Task，并登记给正在运行的 Event Loop。

```text
coroutine object
      ↓ create_task(...)
Task
      ↓ 由它调度
Event Loop
```

如果 `fetch_user()` 和 `fetch_orders()` 各自等待约 100ms，而且彼此没有依赖，那么两个 Task 的等待可以重叠，总时间可能接近 100ms，而不是约 200ms。

注意：`create_task()` 不会强行打断当前代码。当前 Task 要先走到能够让出执行机会的位置，新 Task 才有机会运行。

应用程序通常只在最外层使用：

```python
asyncio.run(main())
```

可以先把它理解成“创建并运行 Event Loop，让 `main()` 跑到结束，然后做收尾并关闭 Event Loop”。

## 脑内执行模型

```text
当前 Task: create U ─ create O ─ await U ........ await O
user Task:                └─ run ─ wait I/O .... finish
orders Task:                  └─ run ─ wait I/O .... finish
                           时间 →
```

关键不是代码里有几个 `await`，而是**同一时间是否存在多个可独立推进的 Task**。

## 常见误解

- **误区：** Task 就是线程。Task 是 asyncio 的异步工作单位；多个 Task 通常仍在同一个 Event Loop 线程中合作式运行。
- **误区：** `create_task()` 一调用，新 Task 就立刻抢占当前代码。当前工作要先让出执行机会。
- **误区：** 两个连续 `await` 就是并发。如果第二个调用直到第一个结束后才开始，通常仍是串行。
- **误区：** Event Loop 能自动打断长时间计算。它不能强行抢占一直运行的普通 Python 代码。

## 本节规则总结

1. Event Loop 负责调度。
2. Task 是可被独立调度的 coroutine 工作。
3. 多个同时存活的 Task 才形成 asyncio 的并发结构。
4. 并发的主要收益来自重叠等待时间。
5. 只并发彼此无数据依赖、且并发确有收益的工作。

## 关键问题

1. coroutine object 与 Task 最大的区别是什么？
2. Event Loop 的核心职责是什么？
3. 为什么 `await fetch_user(); await fetch_orders()` 通常是串行？
4. `create_task()` 后，新 Task 最早什么时候有机会运行？
5. 为什么 Event Loop 不能解决一个长时间不让出的纯 Python 计算？

## 场景命题

Dashboard 同时需要 user 与 orders。它们只依赖同一个 `user_id`，彼此没有数据依赖。把不必要的串行等待改成真正并发。

## 验收

测试会使用可控延迟验证结果正确，并确认两个等待确实发生重叠。

仓库参考实现：

```bash
uv run pytest lessons/02_event_loop_and_task/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/02_event_loop_and_task/tests -v --learner
```
