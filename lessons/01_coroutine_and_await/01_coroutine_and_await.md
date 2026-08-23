# Lesson 01 — 函数被调用后，代码什么时候真正开始执行

## 进入本课前

你已经从 Lesson 00 学过 generator 的“暂停后继续”直觉，以及 `yield` 的基本作用。

除此之外，本课不要求你提前知道下面这些新概念。

## 本课新增术语

- **async（异步）**：一份工作遇到等待时，可以先暂停；程序之后可以继续推进别的工作，而不是整段一起停住。具体怎样推进别的工作，下一课再讲。
- **asyncio**：Python 标准库中组织上面这类 async 工作的一组工具；本课先使用其中两个最外层辅助工具。
- **coroutine（协程）**：一种可以在执行途中暂停、之后再从原位置继续的 async 执行过程。
- **coroutine function（协程函数）**：用 `async def` 定义、调用后会产生 coroutine object 的函数。
- **coroutine object（协程对象）**：调用 coroutine function 后得到的对象；创建它不等于函数体已经开始执行。
- **`await`**：等待右边的 async 工作得到结果；如果结果还没准备好，当前 coroutine 可以先暂停。
- **`asyncio.sleep(delay)`**：让当前 coroutine 至少暂停约 `delay` 秒的工具；课程前半段用它模拟“正在等待外部结果”。
- **Awaitable（可等待对象）**：可以写在 `await` 右边、让当前 coroutine 等待其结果的对象。
- **`asyncio.run(coro)`**：程序最外层用来运行一个 coroutine object、直到它结束的入口工具；内部怎样组织执行在下一课解释。
- **`RuntimeWarning`（运行时警告）**：Python 在程序运行时发现可疑用法后给出的提示；创建 coroutine object 却一直没有等待它，是一种常见触发原因。
- **data dependency（数据依赖）**：后一步必须拿到前一步的结果，才能知道自己该怎样开始。

## 一个例子串起全部术语

下面用“先查订单，再根据订单里的客户编号查客户”串起本课概念。第二次查询必须使用第一次查询的结果，因此这里故意保持正确的先后顺序。代码就是本课的 `case.py`：

```python
import asyncio

async def fetch_order(order_id):
    print(f"fetch_order({order_id}) 函数体开始执行")
    await asyncio.sleep(0.2)  # 暂停当前 coroutine，模拟等待外部结果
    return {"id": order_id, "customer_id": 7}

async def fetch_customer(customer_id):
    print(f"fetch_customer({customer_id}) 函数体开始执行")
    await asyncio.sleep(0.2)
    return {"id": customer_id, "name": "Ada"}

async def main():
    order_coroutine = fetch_order(1)
    # 调用 coroutine function 只得到 coroutine object，上面还没打印任何东西
    print("main：已经创建 coroutine object，函数体尚未开始")
    order = await order_coroutine
    # data dependency：customer 查询必须拿到 order["customer_id"] 才能开始
    customer = await fetch_customer(order["customer_id"])
    print(order, customer)

asyncio.run(main())
```

真实输出：

```text
main：已经创建 coroutine object，函数体尚未开始
fetch_order(1) 函数体开始执行
fetch_customer(7) 函数体开始执行
{'id': 1, 'customer_id': 7} {'id': 7, 'name': 'Ada'}
```

把本课知识点对到代码上：

| 术语或知识点 | 在这个例子里指什么 |
| --- | --- |
| **asyncio** | 提供 `sleep()` 和 `run()`；本课只使用它们的表面行为，不提前展开内部调度机制 |
| **async** | 两个查询在 `asyncio.sleep()` 代表的等待期间都可以暂停；怎样推进其他工作留到下一课 |
| **coroutine** | `fetch_order()`、`fetch_customer()` 和 `main()` 各自运行时形成的可暂停执行过程 |
| **coroutine function** | 用 `async def` 定义的 `fetch_order`、`fetch_customer` 和 `main` |
| **coroutine object** | `order_coroutine = fetch_order(1)` 得到的对象；创建这一刻还没有打印函数体里的文字 |
| **`await`** | `order = await order_coroutine` 推进并等待订单查询；第二个 `await` 推进并等待客户查询 |
| **`asyncio.sleep(delay)`** | 两个查询各自暂停约 0.2 秒，用来稳定模拟一段暂时得不到结果的等待 |
| **Awaitable** | `order_coroutine` 和 `fetch_customer(...)` 返回的 coroutine object 都能放在 `await` 右边 |
| **`asyncio.run(coro)`** | `asyncio.run(main())` 负责从普通程序入口运行 `main()` 到结束 |
| **`RuntimeWarning`** | 正常输出中不会出现“was never awaited”，因为创建的 `order_coroutine` 随后被明确 `await`；它是本例的一项反向验收信号 |
| **data dependency** | `fetch_customer()` 的参数来自 `order["customer_id"]`，所以客户查询不能早于订单结果开始 |

按时间线读输出：

1. `main()` 本身先被调用，产生 coroutine object；`asyncio.run(...)` 从普通程序入口把它运行起来。
2. `fetch_order(1)` 被调用，只产生 coroutine object 并赋给 `order_coroutine`；紧接着先打印“函数体尚未开始”。
3. 执行 `await order_coroutine` 后，`fetch_order()` 函数体才真正开始，所以订单函数的文字出现在下一行。
4. 订单查询等待结束并返回包含 `customer_id` 的字典，`main()` 才能继续。
5. `main()` 读取 `order["customer_id"]`，调用并 `await fetch_customer(7)`，于是打印第二行。
6. 客户查询返回后，最后一行同时打印两个结果。
7. 两次等待没有重叠：第二份工作的输入依赖第一份工作的输出，按顺序执行正是业务要求。

## 本节目标

学完本节，你应该能够：

- 区分 coroutine function 与 coroutine object；
- 判断 `foo()`、`await foo()` 何时真正执行函数体；
- 解释 `await` 的基本含义；
- 使用 `asyncio.run()` 启动最外层 async 入口，并用 `asyncio.sleep()` 构造可观察等待；
- 识别 data dependency；
- 不把“出现 `await`”误判成“已经让多份工作同时进行”。

## 为什么需要学习它

很多人第一次看到 `async def`，会以为调用 coroutine function 后它已经自动开始运行；看到 `await`，又会以为程序自动获得了性能收益。

这一课只解决两个基础问题：

1. 调用 coroutine function 时到底得到了什么；
2. 代码什么时候才真正向前执行。

把这两个问题分清，后面才能正确理解多份工作怎样在同一段时间里都处于进行状态。

## 核心理论

### 1. 先限定 `asyncio.run()` 与 `asyncio.sleep()` 的职责

本课只需要先建立两个可运行入口：

```python
async def main():
    await asyncio.sleep(0.2)

asyncio.run(main())
```

- `main()` 先产生 coroutine object；
- `asyncio.run(...)` 从普通程序入口运行它，直到结束；
- `asyncio.sleep(0.2)` 让当前 coroutine 暂停约 0.2 秒，实际恢复时刻可能稍晚，不能把它当成精密计时器。

下一课才拆开 `asyncio.run()` 内部怎样管理多份工作。本课先集中理解 coroutine object 和 `await`。

### 2. 调用 `async def` 不等于执行函数体

```python
async def fetch_user():
    print("start")
    return {"id": 1}

user_coroutine = fetch_user()
```

执行到 `user_coroutine = fetch_user()` 时，通常还不会打印 `start`。

此时只是：

```text
fetch_user      → coroutine function
fetch_user()    → coroutine object
```

Coroutine object 可以先理解成“一份尚未被推进的 async 工作对象”。

如果只创建后就把它丢掉：

```python
fetch_user()  # 没有 await，也没有交给后续课程的调度工具
```

函数体不会因此完成，Python 还可能提示 `RuntimeWarning: coroutine ... was never awaited`。这个 warning 不是“程序已经在后台替你做完了”，恰好说明这份 coroutine 工作没有被正确消费。

### 3. `await` 才开始等待并推进这份工作

```python
user = await user_coroutine
```

此时当前 coroutine 开始等待 `user_coroutine` 的结果。

如果右边的工作可以继续执行，它会向前推进；如果它暂时需要等待外部结果，当前 coroutine 可以暂停，之后再恢复。

### 4. Coroutine object 是一种 Awaitable

```python
user = await fetch_user()
```

`fetch_user()` 返回 coroutine object，所以它可以直接写在 `await` 右边。

这一课只需要掌握这一种常见 Awaitable；后面的课程会再扩展其他类型。

### 5. `await` 本身不创造“同时进行”

看下面代码：

```python
order = await fetch_order(order_id)
customer = await fetch_customer(order["customer_id"])
```

第二步必须先拿到 `order["customer_id"]`，所以存在 data dependency。

时间线：

```text
开始 fetch_order
      ↓
等待并得到 order
      ↓
读取 customer_id
      ↓
开始 fetch_customer
      ↓
得到 customer
```

第二步直到第一步结束后才知道参数是什么，所以这里按顺序执行是正确的。

### 6. 先判断依赖，再讨论能否重叠等待

在业务代码中，先问：

> 后一步是否必须使用前一步的结果？

如果答案是“是”，就先尊重 dependency。

如果两个工作只共享同一个输入，彼此不需要对方结果，那么它们可能可以更早同时开始；具体怎样做，下一课再解决。

## 脑内执行模型

```text
调用 fetch_order(...)
      ↓
得到 coroutine object
      ↓
await 它
      ↓
真正推进并等待结果
      ↓
拿到 order
      ↓
再创建并 await fetch_customer(...)
```

本课最重要的区分：

```text
创建 coroutine object ≠ 函数体已经运行
await 一个 Awaitable    = 等待并推进它直到得到结果
```

## 常见误解

- **误区：** 调用 `async def` 会立刻执行函数体。  
  **更准确：** 通常只得到 coroutine object。

- **误区：** coroutine object 已经在后台运行。  
  **更准确：** 它只是尚待推进的 async 工作对象。

- **误区：** 创建 coroutine object 后不处理也没关系。
  **更准确：** 它不会自动完成，还可能出现“was never awaited”的 `RuntimeWarning`。

- **误区：** `await` 就表示两份工作同时进行。  
  **更准确：** `await` 直接表达的是“等待右边的 Awaitable”。

- **误区：** async 代码就应该把所有调用尽早开始。  
  **更准确：** 存在 data dependency 时，后一步必须等待前一步结果。

## 本节规则总结

1. `async def` 定义 coroutine function。
2. 调用 coroutine function 得到 coroutine object。
3. 创建 coroutine object 通常不会立刻执行函数体。
4. coroutine object 是 Awaitable，可以被 `await`。
5. `await` 表示等待，不自动制造多份同时进行的工作。
6. 先判断 data dependency，再决定后续执行结构。
7. `asyncio.run()` 只放在程序最外层；`asyncio.sleep()` 只保证至少暂停到指定时间附近。
8. 创建 coroutine object 后必须由清楚的执行路径消费；不能既不 `await` 又直接丢弃。

## 关键问题

1. async 在本课里是什么意思？
2. `async def foo()` 定义出来的 `foo` 是什么？
3. `foo()` 返回什么？为什么这时函数体通常还没执行？
4. `await foo()` 做了什么？
5. Awaitable 是什么？
6. `asyncio.run(main())` 在本课承担什么职责？
7. `asyncio.sleep(0.2)` 是否保证恰好 0.2 秒后恢复？
8. data dependency 是什么？
9. 如果 B 的参数来自 A 的返回结果，B 能否在 A 完成前真正开始？
10. 为什么 `RuntimeWarning: coroutine ... was never awaited` 不表示 coroutine 已经在后台完成？

## 场景命题

一个订单上下文需要先获取 order，再使用其中的 `customer_id` 获取 customer。

请保持真实的 data dependency：先拿到 order，再开始 customer 查询。不要为了“看起来更复杂”而提前开始一个还缺少必要输入的工作。

要求：

- 在 `practice.py` 中实现两个 coroutine function 和一个最外层 `main()`；
- 创建 order coroutine object 后，先打印一行文字证明它的函数体尚未执行；
- 只有拿到 `customer_id` 后才能开始 customer 查询；
- 最终打印两份结果，并确保没有“coroutine was never awaited”警告。

---

完成本课后：继续 [Lesson 02 — 让多份 async 工作交替推进](../02_event_loop_and_task/02_event_loop_and_task.md)。
