# Course Map

按 Lesson 00 → 11 顺序学习即可。这里仅列出每一课要解决的问题。

| Stage | Lesson | 这一课解决的问题 |
|---|---|---|
| 0 | [Lesson 00](lessons/00_python_foundation/README.md) | 普通 Python 里，怎样逐项读取、暂停后继续，并在提前结束时可靠收尾 |
| 1 | [Lesson 01](lessons/01_coroutine_and_await/README.md) | 为什么调用一份工作后，它的代码可能还没有真正开始执行 |
| 2 | [Lesson 02](lessons/02_event_loop_and_task/README.md) | 一份工作等待时，怎样让另一份彼此独立的工作继续推进 |
| 3 | [Lesson 03](lessons/03_structured_concurrency/README.md) | 一组子工作由谁负责，以及父工作结束前怎样确保它们都已结束 |
| 4 | [Lesson 04](lessons/04_cancellation/README.md) | 上层要求停止工作时，代码怎样响应并可靠收尾 |
| 4 | [Lesson 05](lessons/05_timeout_and_errors/README.md) | 等待太久、普通失败和上层停止要求，分别应该怎样影响业务结果 |
| 5 | [Lesson 06](lessons/06_bounded_concurrency/README.md) | 输入很多时，怎样限制同一时刻真正占用有限东西的工作数量 |
| 5 | [Lesson 07](lessons/07_queue_and_backpressure/README.md) | 处理不过来时，怎样限制等待量并让产生工作的一侧自动放慢 |
| 6 | [Lesson 08](lessons/08_real_io/README.md) | 程序真正与另一端交换数据时，怎样把有限容量也纳入设计 |
| 6 | [Lesson 09](lessons/09_blocking_io/README.md) | 一个普通函数长时间等待时，怎样避免其他工作也被迫停住 |
| 7 | [Lesson 10](lessons/10_business_modeling/README.md) | 多个业务步骤谁依赖谁，哪些步骤最早什么时候能开始 |
| 8 | [Lesson 11](lessons/11_production_asyncio/README.md) | 长期运行程序怎样停止、恢复失败、避免重复处理并记录运行情况 |

每课的验收命令写在对应 Lesson 的 `README.md` 末尾。
