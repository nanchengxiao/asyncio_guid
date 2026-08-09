# Lesson 06 — Bounded concurrency

## 本节目标

学完本节，你应该能够：

- 解释为什么任务数量不等于资源容量
- 用 Semaphore 表达并发闸门
- 测量真实峰值并发而不是检查源码
- 避免一次创建无界资源压力

## 为什么需要学习它

你可能有 10 万个 job，但数据库连接池只有 20 条连接。把 10 万个 Task 全部同时推进到数据库，并不会让数据库更快，只会制造排队、内存压力和超时放大。

## 核心理论

Semaphore 表达的是“同时进入某个关键资源区的许可数量”。

```text
很多 jobs
   ↓
Semaphore(10)
   ↓
最多 10 个同时访问 downstream
```

它限制的是 active resource users，而不是总工作数。许可应包围真正消耗稀缺资源的那一段，不要把无关 CPU 准备工作也锁在里面。

## 脑内执行模型

```text
J1 ─ prepare ─ [resource] ─ finish
J2 ─ prepare ─ [resource] ─ finish
J3 ─ prepare ─ wait permit ─ [resource]
                 ↑ peak active <= limit
```

## 常见误解

- **误区：** Semaphore 越小越稳定。过小会浪费下游容量，应该根据资源与 SLA 选择。
- **误区：** 连接池已经有限，所以应用层永远不需要并发限制。排队位置、timeout 和其他资源仍可能需要应用层闸门。
- **误区：** 一次 create_task 10 万个，再用 Semaphore 就完全没有问题。active I/O 有界，但 Task 内存和调度压力仍可能无界。
- **误区：** 并发限制等于 rate limit。一个控制同时在场数量，一个控制单位时间启动量。

## 本节规则总结

1. 先识别稀缺资源，再设置并发闸门。
2. Semaphore 保护资源区，不是装饰整个函数。
3. 测试应观测峰值 active。
4. bounded concurrency 不等于 bounded backlog。
5. 并发限制与速率限制是不同维度。

## 关键问题

1. 为什么 10 万个输入不代表应该有 10 万个 active Task？
2. Semaphore 应围住哪一段代码？
3. 连接池 limit=20 与 Semaphore=100 会发生什么？
4. 如何用测试证明实现不是偷偷串行？
5. 并发限制和 QPS 限制分别控制什么？

## 场景命题

批量调用一个有容量上限的 downstream。输入可以很多，但同一时间进入 `fetch_one` 的调用不能超过 limit，同时在 limit>1 时要保留真实并发。

## 验收

测试记录 active/peak 计数并校验结果；不匹配任何 API 字符串。

仓库参考实现：

```bash
uv run pytest lessons/06_bounded_concurrency/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/06_bounded_concurrency/tests -v --learner
```
