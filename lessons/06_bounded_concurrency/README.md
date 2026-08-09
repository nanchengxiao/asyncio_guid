# Lesson 06 — Bounded concurrency

## 本节目标

学完本节，你应该能够：

- 解释为什么 Task 数量不等于资源容量
- 用 `Semaphore` 表达并发上限
- 区分 active concurrency 与 backlog
- 测量真实峰值并发

## 进入本课前

你已经学过 Task、并发、TaskGroup、timeout 和 cancellation。

本课新增：

- **bounded concurrency（有上限的并发）**：允许并发，但同时进行的数量不能超过明确上限。
- **Semaphore（信号量）**：可以把它理解成有限数量的“通行证”；没有通行证的 Task 要等待。
- **downstream（下游）**：当前代码接下来调用或依赖的外部服务/资源。
- **active concurrency**：此刻真正正在占用稀缺资源的工作数量。
- **backlog（积压）**：已经进入系统但还没轮到处理的工作。

## 为什么需要学习它

你可能有 10 万个 job，但数据库连接池只有 20 条连接。把 10 万个 Task 全部同时推进到数据库，并不会让数据库更快，只会制造排队、内存压力和更多 timeout。

## 核心理论

```python
sem = asyncio.Semaphore(10)

async with sem:
    result = await fetch_one(item)
```

`Semaphore(10)` 表示最多 10 个 Task 同时拿到许可进入这段资源区。第 11 个不会失败，而是等待前面有人释放许可。

```text
很多 jobs
   ↓
Semaphore(10)
   ↓
最多 10 个同时访问 downstream
```

许可应该只包围真正消耗稀缺资源的部分，不要把无关准备工作也一起锁住。

还要注意：Semaphore 只限制 active concurrency。如果一次性创建 10 万个 Task，等待中的 Task 仍然可能形成巨大 backlog。

并发限制也不等于 rate limit：前者控制“同一时刻有多少个”，后者控制“单位时间启动多少个”。rate limit 会在 Lesson 11 正式学习。

## 脑内执行模型

```text
J1 ─ prepare ─ [resource] ─ finish
J2 ─ prepare ─ [resource] ─ finish
J3 ─ prepare ─ wait permit ─ [resource]
                 ↑ active <= limit
```

## 常见误解

- **误区：** Semaphore 越小越安全。太小也会浪费下游本来可以承受的容量。
- **误区：** 有连接池就永远不需要应用层并发限制。不同资源可能有不同容量和排队边界。
- **误区：** 创建 10 万个 Task，再加 Semaphore 就完全有界。active I/O 有界，但等待中的 Task 数量仍可能很大。
- **误区：** 并发限制就是“每秒请求数”限制。两者控制不同维度。

## 本节规则总结

1. 先识别稀缺资源，再设置并发上限。
2. Semaphore 保护真正消耗资源的代码段。
3. 测试应观察峰值 active。
4. bounded concurrency 不等于 bounded backlog。
5. 并发限制与速率限制不是一回事。

## 关键问题

1. 为什么 10 万个输入不代表应该有 10 万个 active Task？
2. `Semaphore(10)` 的 10 表示什么？
3. downstream 是什么意思？
4. Semaphore 应围住哪一段代码？
5. 为什么 bounded concurrency 仍可能有巨大 backlog？
6. 并发限制和速率限制分别控制什么？

## 场景命题

批量调用一个容量有限的 downstream。输入可以很多，但同一时间进入 `fetch_one` 的调用不能超过 `limit`；当 `limit > 1` 时也不能退化成完全串行。

## 验收

测试会记录 active/peak 计数，确认结果正确、峰值不超过 `limit`，同时保留真实并发。

仓库参考实现：

```bash
uv run pytest lessons/06_bounded_concurrency/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/06_bounded_concurrency/tests -v --learner
```
