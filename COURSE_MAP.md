# Course Map

这张图只负责告诉你“下一课解决什么问题”，不提前教授课程术语。术语会在对应 Lesson 第一次进入主线时解释。

| Stage | Lesson | 这一课解决的问题 |
|---|---|---|
| 0 | [Lesson 00](lessons/00_python_foundation/README.md) | 普通 Python 里，怎样逐项读取、暂停后继续，并在提前结束时可靠收尾 |
| 1 | [Lesson 01](lessons/01_coroutine_and_await/README.md) | 异步函数被调用后得到什么，代码又在什么时候真正执行 |
| 2 | [Lesson 02](lessons/02_event_loop_and_task/README.md) | 一份异步工作等待时，程序怎样让其他独立工作继续推进 |
| 3 | [Lesson 03](lessons/03_structured_concurrency/README.md) | 一组子工作由谁负责，以及父工作结束前怎样确保它们都已结束 |
| 4 | [Lesson 04](lessons/04_cancellation/README.md) | 上层要求停止工作时，代码怎样响应并可靠收尾 |
| 4 | [Lesson 05](lessons/05_timeout_and_errors/README.md) | 等待太久、普通失败和上层停止请求，分别应该怎样影响业务结果 |
| 5 | [Lesson 06](lessons/06_bounded_concurrency/README.md) | 输入很多时，怎样限制同时占用稀缺资源的工作数量 |
| 5 | [Lesson 07](lessons/07_queue_and_backpressure/README.md) | 下游处理不过来时，怎样限制等待量并让上游自动放慢 |
| 6 | [Lesson 08](lessons/08_real_io/README.md) | 真实网络调用有哪些有限资源，怎样把它们纳入设计 |
| 6 | [Lesson 09](lessons/09_blocking_io/README.md) | 普通同步函数长时间等待时，怎样避免拖住其他异步工作 |
| 7 | [Lesson 10](lessons/10_business_modeling/README.md) | 多个业务步骤谁依赖谁，哪些步骤最早什么时候能开始 |
| 8 | [Lesson 11](lessons/11_production_asyncio/README.md) | 一个长期运行的服务怎样处理停止、失败恢复、重复请求和运行状态记录 |

学习时按 Lesson 00 → 11 顺序前进即可。每课的验收命令写在对应 Lesson 的 `README.md` 末尾。
