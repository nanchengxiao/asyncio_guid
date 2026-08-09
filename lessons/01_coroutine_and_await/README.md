# Lesson 01 — 异步函数何时真正执行

## 进入本课前

你已经从 Lesson 00 学过 generator 的“暂停后继续”直觉，以及 `yield` 的基本作用。

除此之外，本课不要求任何异步知识。

## 本课新增术语

- **async（异步）**：一份工作遇到等待时，可以先暂停；程序之后可以继续推进别的工作，而不是整段一起停住。具体怎样推进别的工作，下一课再讲。
- **coroutine（协程）**：一种可以在执行途中暂停、之后再从原位置继续的异步执行过程。
- **coroutine function（协程函数）**：用 `async def` 定义、调用后会产生 coroutine object 的函数。
- **coroutine object（协程对象）**：调用 coroutine function 后得到的对象；创建它不等于函数体已经开始执行。
- **`await`**：等待右边的异步工作得到结果；如果结果还没准备好，当前 coroutine 可以先暂停。
- **Awaitable（可等待对象）**：可以写在 `await` 右边、让当前 coroutine 等待其结果的对象。
- **data dependency（数据依赖）**：后一步必须拿到前一步的结果，才能知道自己该怎样开始。

## 本节目标

学完本节，你应该能够：

- 区分 coroutine function 与 coroutine object；
- 判断 `foo()`、`await foo()` 何时真正执行函数体；
- 解释 `await` 的基本含义；
- 识别 data dependency；
- 不把“出现 `await`”误判成“已经让多份工作同时进行”。

## 为什么需要学习它

很多人第一次看到 `async def`，会以为调用异步函数后它已经自动开始运行；看到 `await`，又会以为程序自动获得了性能收益。

这一课只解决两个基础问题：

1. 调用异步函数时到底得到了什么；
2. 代码什么时候才真正向前执行。

把这两个问题分清，后面才能正确理解多份异步工作怎样同时处于进行状态。

## 核心理论

### 1. 调用 `async def` 不等于执行函数体

```python
async def fetch_user():
    print("start")
    return {"id": 1}

coro = fetch_user()
```

执行到 `coro = fetch_user()` 时，通常还不会打印 `start`。

此时只是：

```text
fetch_user      → coroutine function
fetch_user()    → coroutine object
```

Coroutine object 可以先理解成“一份尚未被推进的异步工作对象”。

### 2. `await` 才开始等待并推进这份工作

```python
user = await coro
```

此时当前 coroutine 开始等待 `coro` 的结果。

如果右边的工作可以继续执行，它会向前推进；如果它暂时需要等待外部结果，当前 coroutine 可以暂停，之后再恢复。

### 3. Coroutine object 是一种 Awaitable

```python
user = await fetch_user()
```

`fetch_user()` 返回 coroutine object，所以它可以直接写在 `await` 右边。

这一课只需要掌握这一种常见 Awaitable；后面的课程会再扩展其他类型。

### 4. `await` 本身不创造“同时进行”

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

### 5. 先判断依赖，再讨论能否重叠等待

在业务代码中，先问：

> 后一步是否必须使用前一步的结果？

如果答案是“是”，就先尊重依赖。

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
  **更准确：** 它只是尚待推进的异步工作对象。

- **误区：** `await` 就表示两份工作同时进行。  
  **更准确：** `await` 直接表达的是“等待右边的 Awaitable”。

- **误区：** 异步代码就应该把所有调用尽早开始。  
  **更准确：** 存在 data dependency 时，后一步必须等待前一步结果。

## 本节规则总结

1. `async def` 定义 coroutine function。
2. 调用 coroutine function 得到 coroutine object。
3. 创建 coroutine object 通常不会立刻执行函数体。
4. coroutine object 是 Awaitable，可以被 `await`。
5. `await` 表示等待，不自动制造多份同时进行的工作。
6. 先判断 data dependency，再决定后续执行结构。

## 关键问题

1. `async def foo()` 定义出来的 `foo` 是什么？
2. `foo()` 返回什么？为什么这时函数体通常还没执行？
3. `await foo()` 做了什么？
4. Awaitable 是什么？
5. data dependency 是什么？
6. 如果 B 的参数来自 A 的返回结果，B 能否在 A 完成前真正开始？

## 场景命题

一个订单上下文需要先获取 order，再使用其中的 `customer_id` 获取 customer。

请保持真实的数据依赖：先拿到 order，再开始 customer 查询。不要为了“看起来更异步”而提前开始一个还缺少必要输入的工作。

## 验收

测试会验证：

- 创建 coroutine object 不会提前触发业务调用；
- order 查询先完成；
- customer 查询只能在拿到 `customer_id` 后开始；
- 最终返回 `{order, customer}`。

仓库参考实现：

```bash
uv run pytest lessons/01_coroutine_and_await/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/01_coroutine_and_await/tests -v --learner
```
