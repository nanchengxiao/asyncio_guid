# Lesson 06 — Bounded concurrency

## 本节目标

学完本节，你应该能够：

- 解释为什么“Task 数量”不等于“资源允许的同时使用数量”
- 理解 `Semaphore` 是什么，以及它限制的是什么
- 区分 active concurrency（正在使用资源的并发量）与等待中的工作
- 通过测试测量真实峰值并发

## 进入本课前

你已经学过：Task、并发、TaskGroup、timeout 和 cancellation。

这一课新增 **bounded concurrency、Semaphore、downstream、active concurrency、backlog**。

## 为什么需要学习它

假设你有 10 万个 job（待处理工作），但数据库最多只允许 20 个连接。

把 10 万个 Task 全部同时推进到数据库，不会让数据库突然拥有 10 万条连接，只会让大量工作排队，增加内存占用，并让 timeout 更容易发生。

所以生产系统不仅要问：

> 能不能并发？

还要问：

> **最多允许多少份工作同时占用这个资源？**

## 核心理论

### 1. bounded concurrency 是什么

**bounded concurrency（有上限的并发）**就是：

> 允许多份工作并发，但同时进行的数量不能超过一个明确上限。

例如最多 10 个请求同时访问某个服务。

### 2. Semaphore 是什么

`asyncio.Semaphore` 可以理解成一组有限数量的“通行证”。

```python
sem = asyncio.Semaphore(10)
```

表示最多有 10 个 Task 同时拿到许可进入受保护的代码段。

```python
async with sem:
    return await fetch_one(item)
```

第 11 个 Task 到来时，并不会失败；它会等待前面的 Task 释放许可。

```text
很多 Task
   ↓
Semaphore(10)
   ↓
最多 10 个同时进入资源区
```

### 3. downstream 是什么

工程里常说 **downstream（下游）**，意思是：

> 当前代码接下来要调用、依赖的外部服务或资源。

例如你的 API 调用数据库，那么数据库就是这个 API 的 downstream；你的服务调用支付服务，支付服务也是 downstream。

### 4. active concurrency 是什么

**active concurrency** 可以理解成：

> 此刻真正正在占用稀缺资源的工作数量。

例如：

```text
1000 个输入
20 个 Task 正在查询数据库
980 个还在等待
```

active concurrency 是 20，不是 1000。

### 5. backlog 是什么

**backlog（积压工作）**指的是：

> 已经进入系统、但还没轮到真正处理的工作。

Semaphore 可以限制“同时有多少工作进入资源区”，但如果你一次性创建 10 万个 Task，这 10 万个 Task 本身仍然存在，其中大量工作只是等待许可。

所以：

> bounded active concurrency 不等于 bounded backlog。

下一课会用 Queue 专门控制积压量。

### 6. Semaphore 应该包住哪一段

应该只包住真正消耗稀缺资源的部分：

```python
prepare_data(item)  # 不占下游连接

async with sem:
    result = await call_downstream(item)  # 真正占用稀缺资源

format_result(result)
```

如果把整个函数都锁住，会把本来可以同时做的无关工作也限制住。

### 7. 并发限制和速率限制不是一回事

并发限制回答：

> 同一时刻最多有多少个？

速率限制回答：

> 一秒钟最多启动多少个？

例如最多 10 个同时请求，不代表每秒只能发 10 个请求。如果每个请求 10ms 完成，一秒内可能完成很多批。

速率限制会在 Lesson 11 正式学习。

## 脑内执行模型

```text
J1 ─ prepare ─ [resource] ─ finish
J2 ─ prepare ─ [resource] ─ finish
J3 ─ prepare ─ wait permit ─ [resource]
                 ↑
           同时在资源区的数量 <= limit
```

## 常见误解

- **误区：Semaphore 越小越安全。** 太小会浪费下游本来能够承受的容量。
- **误区：有连接池就永远不需要应用层并发限制。** 不同资源可能有不同容量，排队位置也会影响 timeout 和内存压力。
- **误区：创建 10 万个 Task，再放一个 Semaphore 就完全有界了。** active I/O 有上限，但等待中的 Task 数量仍可能很大。
- **误区：并发限制就是“每秒请求数”限制。** 一个控制同时在场数量，一个控制单位时间启动量。

## 本节规则总结

1. 先找出真正稀缺的资源。
2. `Semaphore` 限制同时进入资源区的 Task 数量。
3. 并发闸门只包住真正消耗该资源的代码。
4. active concurrency 与 backlog 是两个不同问题。
5. 测试应观察实际峰值并发，而不是检查代码里有没有写 `Semaphore`。

## 关键问题

1. 为什么 10 万个输入不代表应该有 10 万个 active Task？
2. `Semaphore(10)` 的“10”表示什么？
3. downstream 是什么意思？
4. Semaphore 应该围住整个函数，还是只围住真正占用资源的部分？为什么？
5. 为什么 bounded concurrency 仍然可能有巨大 backlog？
6. 并发限制和速率限制分别控制什么？

## 场景命题

批量调用一个容量有限的 downstream。输入可以很多，但同一时间进入 `fetch_one` 的调用不能超过 `limit`；同时，当 `limit > 1` 时也不能退化成完全串行。

## 验收

测试会记录当前 active 数量和历史 peak（峰值），确认：

- 所有结果正确；
- peak 从不超过 `limit`；
- `limit > 1` 时确实存在并发，而不是偷偷串行。

仓库参考实现：

```bash
uv run pytest lessons/06_bounded_concurrency/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/06_bounded_concurrency/tests -v --learner
```
