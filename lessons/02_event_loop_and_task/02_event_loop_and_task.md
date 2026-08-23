# Lesson 02 — 让多份 async 工作交替推进

## 进入本课前

你已经学过 coroutine、Awaitable、`await`，以及 data dependency。

## 本课新增术语

- **Event Loop（事件循环）**：asyncio 的调度中心，负责让当前可以继续的 async 工作轮流向前执行。
- **Task（任务）**：被 Event Loop 正式登记、拥有自己执行进度的一份 coroutine 工作。
- **scheduling（调度）**：决定接下来让哪一个当前可以继续的 Task 向前执行。
- **concurrency（并发）**：多份工作在同一段时间内都处于进行状态；一份工作等待时，另一份可以推进。
- **I/O（输入/输出）**：程序需要从外部取得数据或把数据交出去的操作；这类操作常常包含等待，例如读取文件。
- **thread（线程）**：程序的一条执行路径；本课只需要知道 Event Loop 通常在一条 thread 里运行。
- **`asyncio.create_task()`**：把 coroutine object 包装成 Task，并交给当前 Event Loop 管理的工具。
- **`asyncio.run()`**：在程序最外层创建并运行 Event Loop，让指定的 async 入口一直执行到结束的工具。

## 本节目标

学完本节，你应该能够：

- 解释 Event Loop 和 Task 分别负责什么；
- 说明 concurrency 为什么来自多个同时存活的 Task；
- 预测 `create_task()` 后的基本执行时间线；
- 识别可以 concurrency 的独立 I/O；
- 解释为什么 `await` 数量本身不能证明多份等待已经重叠。

## 为什么需要学习它

前一课知道 coroutine 可以暂停，但还没有回答：

> 它暂停以后，程序为什么还能去做别的事情？

Event Loop 和 Task 就是这个问题的核心。

如果不理解这两个对象，很容易把“写了多个 `await`”误以为“等待已经重叠”。

## 核心理论

### 1. Coroutine object 还不是独立 Task

```python
user_coro = fetch_user()
orders_coro = fetch_orders()
```

这里得到两个 coroutine object，但并不能仅凭这两行判断它们会 concurrency 推进。

要让它们成为两份可以被 Event Loop 分别 scheduling 的工作，可以创建 Task：

```python
user_task = asyncio.create_task(fetch_user())
orders_task = asyncio.create_task(fetch_orders())
```

关系可以先记成：

```text
coroutine object
      ↓ create_task(...)
Task
      ↓ 由它 scheduling
Event Loop
```

### 2. 多个 Task 才给 Event Loop 多个独立推进对象

```python
user_task = asyncio.create_task(fetch_user())
orders_task = asyncio.create_task(fetch_orders())

user = await user_task
orders = await orders_task
```

假设两个调用各自都需要等待约 100ms，而且彼此没有 data dependency。

两个 Task 都已经存在时，一个 Task 进入 I/O 等待，Event Loop 就可以推进另一个 Task。这样两段等待时间可以重叠，总耗时可能接近 100ms，而不是约 200ms。

### 3. `create_task()` 不会立刻中断当前代码

创建 Task 后，新 Task 已经登记给 Event Loop，但当前正在执行的代码不会因为这一行立刻停下来。

当前 Task 需要先走到一个能够暂停或结束的位置，Event Loop 才有机会安排其他 Task 向前执行。

所以：

```python
asyncio.create_task(do_work())
print("current continues")
```

不能机械背成“`do_work()` 一定在 `print` 之前开始”。要看当前代码什么时候把执行机会交回 Event Loop。

### 4. 两个连续 `await` 仍可能完全按顺序

```python
user = await fetch_user()
orders = await fetch_orders()
```

这里第二个调用只有在第一个 `await` 完成后才开始。

```text
fetch_user  ─ wait ─ done
                    ↓
fetch_orders       ─ wait ─ done
```

这仍然是顺序等待。

### 5. `asyncio.run()` 负责最外层入口

应用程序通常在最外层写：

```python
async def main():
    ...

asyncio.run(main())
```

可以先把它理解成：

```text
创建 Event Loop
      ↓
运行 main()
      ↓
不断 scheduling Task
      ↓
main() 结束
      ↓
做收尾并关闭 Event Loop
```

业务函数内部通常不需要自己反复创建新的 Event Loop。

## 脑内执行模型

```text
当前 Task: create U ─ create O ─ await U ........ await O
user Task:                └─ run ─ wait I/O .... finish
orders Task:                  └─ run ─ wait I/O .... finish
                           时间 →
```

图里的 `run / wait / finish` 只是“执行 / 等待 / 结束”的短标签，不是新的机制。

关键问题不是“代码里有几个 `await`”，而是：

> 同一时间是否存在多个可以被 Event Loop 分别推进的 Task？

## 常见误解

- **误区：** Task 就是 thread。**更准确：** Task 是 asyncio 的工作单位；多个 Task 通常仍由同一条 Event Loop thread 轮流推进。
- **误区：** `create_task()` 一调用，新 Task 就立刻中断当前代码。**更准确：** 当前工作要先把执行机会交回 Event Loop。
- **误区：** 两个连续 `await` 就是 concurrency。**更准确：** 如果第二个调用直到第一个完成后才开始，仍然是顺序等待。
- **误区：** Event Loop 能自动打断长时间运行的普通 Python 代码。**更准确：** 一段一直不暂停的普通 Python 代码会持续占着当前 thread。
- **误区：** concurrency 越多越好。
  **更准确：** 本课只建立执行模型；资源容量会在后面的课程专门处理。

## 本节规则总结

1. Event Loop 负责 scheduling。
2. Task 是可以被独立 scheduling 的 coroutine 工作。
3. 多个同时存活的 Task 才形成 asyncio 的 concurrency 结构。
4. Concurrency 的主要收益来自重叠等待时间。
5. `create_task()` 创建独立 Task，但不会立刻中断当前代码。
6. 先判断 data dependency，再决定哪些工作值得同时开始。

## 关键问题

1. coroutine object 与 Task 最大的区别是什么？
2. Event Loop 的核心职责是什么？
3. concurrency 在本课中的白话含义是什么？
4. 为什么 `await fetch_user(); await fetch_orders()` 通常仍是顺序等待？
5. `create_task()` 后，新 Task 最早什么时候有机会真正运行？
6. 为什么 Event Loop 不能解决一段长时间不暂停的普通 Python 计算？

## 场景命题

一个页面同时需要 user 与 orders。两份数据只共享同一个 `user_id`，彼此没有 data dependency。

请把不必要的顺序等待改成真正 concurrency，并保证函数返回前自己创建的两份工作都已经结束。
