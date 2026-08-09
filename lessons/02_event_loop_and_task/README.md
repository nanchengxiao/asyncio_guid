# Lesson 02 — Event loop and task

## 本节目标

学完本节，你应该能够：

- 解释 Coroutine → Task → Event Loop 的关系
- 说明并发为何来自多个同时存活的 Task
- 预测 create_task 后的执行时间线
- 识别可以并发的独立 I/O

## 为什么需要学习它

业务里真正的收益通常不是“把函数改成 async”，而是让互不依赖的等待时间重叠。但如果不理解 Task 的调度边界，很容易把串行代码误以为并发。

## 核心理论

`Task` 给 coroutine 增加了独立的生命周期与调度身份。

```python
user_task = asyncio.create_task(fetch_user())
orders_task = asyncio.create_task(fetch_orders())
user = await user_task
orders = await orders_task
```

现在两个 Task 都已注册到事件循环。当前 Task 下一次让出控制权后，它们都可能推进。若两个请求分别等待 100ms，总耗时接近 100ms，而不是 200ms。

应用程序通常只在最外层用一次 `asyncio.run(main())` 创建、运行并关闭事件循环。不要为了每个业务函数手工 `get_event_loop()` / `run_until_complete()`。`asyncio.gather()` 可以聚合多个 awaitable，但课程更关心“这些 Task 的生命周期属于谁”，后续会优先使用 `TaskGroup` 表达结构化 ownership。

## 脑内执行模型

```text
main     create U  create O  await U ........ await O
user                  ███ wait........██
orders                    ███ wait........██
                         时间 →
```

关键不是 `await` 数量，而是同一时间是否存在多个可推进的 Task。

## 常见误解

- **误区：** create_task 等于创建线程。Task 仍由同一事件循环线程合作式调度。
- **误区：** Task 一创建就立刻抢占当前代码。当前 Task 要先到达可让出点。
- **误区：** gather 才能产生并发。多个 Task 已经足以形成并发；gather 只是等待/聚合工具之一。
- **误区：** 并发越多越好。资源容量问题会在 Stage 5 处理。

## 本节规则总结

1. Task 是由事件循环调度的 coroutine 生命周期容器。
2. 多个同时存活的 Task 才提供 asyncio 并发结构。
3. 事件循环不会强行打断正在运行的 Python 代码。
4. create_task 之后仍要明确谁持有和等待 Task。
5. 只并发没有数据依赖且收益值得的工作。

## 关键问题

1. 为什么 `await fetch_user(); await fetch_orders()` 通常串行？
2. create_task 后新 Task 最早什么时候有机会运行？
3. 事件循环为什么不能解决一个长时间纯 Python 计算？
4. 如果创建 Task 后马上丢掉引用，生命周期设计有什么隐患？
5. 如何从时间线判断两个 I/O 是否重叠？

## 场景命题

Dashboard 同时需要 user 与 orders，它们只依赖同一个 user_id，彼此无依赖。把不必要的串行等待改成真正并发，并返回聚合结果。

## 验收

测试使用受控延迟验证正确性与重叠执行；阈值留有余量避免 flaky。

仓库参考实现：

```bash
uv run pytest lessons/02_event_loop_and_task/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/02_event_loop_and_task/tests -v --learner
```
