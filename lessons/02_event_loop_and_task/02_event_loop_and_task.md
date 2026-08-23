# Lesson 02 — 让多份 async 工作交替推进

## 进入本课前

你已经学过 coroutine、Awaitable、`await`、`asyncio.run()`、`asyncio.sleep()`，以及 data dependency。

## 本课新增术语

- **Event Loop（事件循环）**：asyncio 的调度中心，负责让当前可以继续的 async 工作轮流向前执行。
- **Task（任务）**：被 Event Loop 正式登记、拥有自己执行进度的一份 coroutine 工作。
- **scheduling（调度）**：决定接下来让哪一个当前可以继续的 Task 向前执行。
- **concurrency（并发）**：多份工作在同一段时间内都处于进行状态；一份工作等待时，另一份可以推进。
- **I/O（输入/输出）**：程序需要从外部取得数据或把数据交出去的操作；这类操作常常包含等待，例如读取文件。
- **thread（线程）**：程序的一条执行路径；本课只需要知道 Event Loop 通常在一条 thread 里运行。
- **`asyncio.create_task()`**：把 coroutine object 包装成 Task，并交给当前 Event Loop 管理的工具。
- **`time.perf_counter()`**：读取一个适合测量经过时间的计时值；用结束值减开始值可以比较两种写法耗时，不表示当前日期时间。

## 一个例子串起全部术语

下面用“组装用户首页”对比两种写法。用户资料和订单列表只共享同一个 `user_id`，彼此没有 data dependency，因此两段等待可以重叠。代码就是本课的 `case.py`：

```python
import asyncio
import time

async def fetch_user(user_id):
    print("[user] 开始")
    await asyncio.sleep(0.3)
    print("[user] 结束")
    return {"id": user_id}

async def fetch_orders(user_id):
    print("[orders] 开始")
    await asyncio.sleep(0.3)
    print("[orders] 结束")
    return [{"id": 101}]

async def dashboard_sequential(user_id):
    # 反例：两个连续 await，第二个直到第一个完成后才开始
    start = time.perf_counter()
    user = await fetch_user(user_id)
    orders = await fetch_orders(user_id)
    return time.perf_counter() - start, {"user": user, "orders": orders}

async def dashboard_concurrent(user_id):
    # 正例：两个 Task 同时存活，一段等待时 Event Loop 推进另一段
    start = time.perf_counter()
    user_task = asyncio.create_task(fetch_user(user_id))
    orders_task = asyncio.create_task(fetch_orders(user_id))
    user = await user_task        # 本例 Task 未完成，所以这里暂停并交回执行机会
    orders = await orders_task
    return time.perf_counter() - start, {"user": user, "orders": orders}

async def main():
    print("=== 顺序等待 ===")
    sequential_seconds, sequential_result = await dashboard_sequential(1)
    print("=== concurrency ===")
    concurrent_seconds, concurrent_result = await dashboard_concurrent(1)
    print(f"两种写法的业务结果相同：{sequential_result == concurrent_result}")
    print(concurrent_result)
    print(f"顺序等待 ≈ {sequential_seconds:.2f}s；"
          f"concurrency ≈ {concurrent_seconds:.2f}s")

asyncio.run(main())
```

一次运行的输出如下；具体耗时会随机器略有变化：

```text
=== 顺序等待 ===
[user] 开始
[user] 结束
[orders] 开始
[orders] 结束
=== concurrency ===
[user] 开始
[orders] 开始
[user] 结束
[orders] 结束
两种写法的业务结果相同：True
{'user': {'id': 1}, 'orders': [{'id': 101}]}
顺序等待 ≈ 0.60s；concurrency ≈ 0.30s
```

把本课知识点对到代码上：

| 术语或知识点 | 在这个例子里指什么 |
| --- | --- |
| **Event Loop** | 由 `asyncio.run(main())` 创建并运行；两份 Task 等待时由它选择当前可以继续的工作 |
| **Task** | `user_task` 与 `orders_task` 是两份分别保存执行进度的工作 |
| **scheduling** | `dashboard_concurrent()` 走到 `await user_task` 后交出执行机会，Event Loop 随后推进两份 Task |
| **concurrency** | 用户查询和订单查询在同一段约 0.3 秒内都处于进行状态，两段等待发生重叠 |
| **I/O** | 本例用 `asyncio.sleep(0.3)` 模拟“等待外部输入或输出结果”，还没有连接真实外部系统 |
| **thread** | 代码没有创建额外 thread；这两份 Task 通常由同一条 Event Loop thread 交替推进 |
| **`asyncio.create_task()`** | 把两个 coroutine object 分别包装成 `user_task` 和 `orders_task` |
| **`asyncio.run()`** | 负责最外层入口：启动 Event Loop、运行 `main()`，并在它结束后收尾 |
| **`time.perf_counter()`** | 两个 dashboard 函数分别记录开始值和结束值，用差值比较约 0.6 秒与约 0.3 秒 |

按时间线比较两种写法：

1. 顺序版本先打印 user 开始与结束，之后才出现 orders 开始；输出本身就证明第二份工作此前没有启动。
2. 两段约 0.3 秒的等待首尾相接，因此总计约 0.6 秒。
3. `dashboard_concurrent()` 先连续创建 `user_task` 与 `orders_task`；创建动作登记工作，但不会在这一行强行中断当前代码。
4. 当前代码走到 `await user_task` 后暂停，Event Loop 获得 scheduling 机会。
5. Concurrency 版本先连续打印 user 开始与 orders 开始，两份 Task 随后都到达各自的 `asyncio.sleep(0.3)`，等待时间开始重叠。
6. 约 0.3 秒后两份工作都具备继续条件；取得 `user_task` 结果后，`orders_task` 通常也已完成。
7. 比较行打印 `True`，直接证明两种写法得到相同业务结果；只有第二种让两份彼此独立的等待 concurrency 推进。

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
user_coroutine = fetch_user()
orders_coroutine = fetch_orders()
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

### 6. `create_task()` 之后必须保留并等待 Task

下面这种写法会创建一份独立工作，却立刻丢掉调用方手里的 Task 引用：

```python
asyncio.create_task(fetch_user(1))
```

调用方之后很难明确取得结果或判断它何时结束。本课示例因此把两个 Task 分别保存在 `user_task`、`orders_task`，并在正常路径上逐一 `await`。

还要看清本课示例的边界：如果 `await user_task` 提前抛出异常，单纯按顺序 `await` 两个 Task 并不足以自动保证另一个也被妥善收尾。为了先集中学习 scheduling，本课只演示两份工作都正常完成的路径；下一课会解决“一组工作中有一份失败时，整组怎样在同一边界内结束”。不要把本课的手动写法直接当成完整的失败处理模板。

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
- **误区：** 代码每执行一次 `await`，就一定会切换到其他 Task。**更准确：** 只有右边结果尚未就绪、当前 Task 确实需要暂停时，Event Loop 才得到这次调度机会；本例第一次 `await user_task` 时它尚未完成。
- **误区：** 两个连续 `await` 就是 concurrency。**更准确：** 如果第二个调用直到第一个完成后才开始，仍然是顺序等待。
- **误区：** Event Loop 能自动打断长时间运行的普通 Python 代码。**更准确：** 一段一直不暂停的普通 Python 代码会持续占着当前 thread。
- **误区：** 调用 `create_task()` 后可以不保存返回的 Task。**更准确：** 创建者还需要取得结果、观察失败并确认结束；本课先在正常路径上显式等待两份 Task。
- **误区：** concurrency 越多越好。
  **更准确：** 本课只建立执行模型；资源容量会在后面的课程专门处理。

## 本节规则总结

1. Event Loop 负责 scheduling。
2. Task 是可以被独立 scheduling 的 coroutine 工作。
3. 多个同时存活的 Task 才形成 asyncio 的 concurrency 结构。
4. Concurrency 的主要收益来自重叠等待时间。
5. `create_task()` 创建独立 Task，但不会立刻中断当前代码。
6. `await` 只有在右边结果尚未就绪时才会让当前 Task 暂停，不能把每个 `await` 机械理解成一次切换。
7. 先判断 data dependency，再决定哪些工作值得同时开始。
8. 不要丢弃 `create_task()` 返回的 Task；创建工作也意味着之后要观察它的结果与结束。
9. 手动逐个 `await` 只展示正常调度路径，不自动解决“一份失败时另一份怎样收尾”。

## 关键问题

1. coroutine object 与 Task 最大的区别是什么？
2. Event Loop 的核心职责是什么？
3. concurrency 在本课中的白话含义是什么？
4. 为什么 `await fetch_user(); await fetch_orders()` 通常仍是顺序等待？
5. `create_task()` 后，新 Task 最早什么时候有机会真正运行？
6. 为什么 Event Loop 不能解决一段长时间不暂停的普通 Python 计算？
7. 为什么耗时比较要用两次 `time.perf_counter()` 的差值，而不能把单次返回值当成日期时间？
8. 为什么不应该调用 `create_task()` 后立刻丢弃它返回的 Task？
9. 如果第一个 `await task` 提前失败，为什么手动逐个等待的写法还不是完整的整组 failure 方案？
10. 为什么不能把每一次 `await` 都理解成“Event Loop 一定切换到另一份 Task”？

## 场景命题

一个页面同时需要 user 与 orders。两份数据只共享同一个 `user_id`，彼此没有 data dependency。

请把不必要的顺序等待改成真正 concurrency，并保证函数返回前自己创建的两份工作都已经结束。

要求：

- 先实现连续两个 `await` 的顺序版本，再实现创建两个 Task 的 concurrency 版本；
- 为两份查询分别打印“开始”和“结束”，仅凭输出就能判断等待是否重叠；
- 记录两种写法的总耗时，但不要断言毫秒级精确值；
- 两个版本返回相同业务结果；
- concurrency 版本返回前必须明确等待自己创建的两个 Task。

本课只验收两份查询正常完成时的 scheduling 与耗时；不要自行加入尚未学习的整组 failure 机制。进入下一课后，再回头把这种手动创建与等待改成具有统一边界的版本。

---

完成本课后：继续 [Lesson 03 — 让一组工作在同一个边界内开始和结束](../03_structured_concurrency/03_structured_concurrency.md)。
