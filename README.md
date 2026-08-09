# asyncio_guid

## 课程定位

一套面向**已有普通 Python 基础、但可以完全没有 asyncio 基础**的实践课程。

课程从“代码什么时候真正执行、等待时发生什么”开始，逐步走到真实网络调用、业务依赖建模和服务运行边界。重点不是记 API，而是先理解执行过程，再写出可维护、可测试的异步代码。

课程统一使用 **Python >= 3.11**。

## 前置要求

开始课程前，只默认你已经会普通 Python 的这些内容：

- 变量、函数、参数与返回值；
- `if` / `for` / `while`；
- list / dict 等常见容器；
- 基本的模块导入；
- 知道异常是什么，并见过 `try / except`。

除此之外不默认你掌握任何异步、并发或工程术语。课程需要的新概念会在第一次进入主线时先用一句白话解释。

## 学习路线

| Stage | Lesson | 这一课解决的问题 |
|---|---|---|
| 0 | [Lesson 00](lessons/00_python_foundation/README.md) | 补齐逐项读取、暂停后继续、以及可靠收尾所需的 Python 基础 |
| 1 | [Lesson 01](lessons/01_coroutine_and_await/README.md) | 理解异步函数被调用后得到什么，以及代码何时真正开始执行 |
| 2 | [Lesson 02](lessons/02_event_loop_and_task/README.md) | 让彼此独立的等待时间真正重叠，而不是看起来“异步”却仍按顺序等待 |
| 3 | [Lesson 03](lessons/03_structured_concurrency/README.md) | 让一组子工作有明确负责人，并保证父工作结束前它们已经结束 |
| 4 | [Lesson 04](lessons/04_cancellation/README.md) | 正确响应“停止这份工作”的请求，并保证资源可靠收尾 |
| 4 | [Lesson 05](lessons/05_timeout_and_errors/README.md) | 给等待设置时间上限，并区分不同失败结果应怎样影响业务 |
| 5 | [Lesson 06](lessons/06_bounded_concurrency/README.md) | 限制同时占用稀缺资源的工作数量 |
| 5 | [Lesson 07](lessons/07_queue_and_backpressure/README.md) | 限制等待中的工作数量，并在处理不过来时让上游自动放慢 |
| 6 | [Lesson 08](lessons/08_real_io/README.md) | 把真实网络连接和服务器容量放进资源模型 |
| 6 | [Lesson 09](lessons/09_blocking_io/README.md) | 避免普通同步函数长时间占住异步程序的执行路径 |
| 7 | [Lesson 10](lessons/10_business_modeling/README.md) | 先画清业务依赖，再决定每份工作最早何时可以开始 |
| 8 | [Lesson 11](lessons/11_production_asyncio/README.md) | 把停止服务、失败恢复、重复请求保护和运行状态记录组合起来 |

更紧凑的 Stage → Lesson 路线图见 [`COURSE_MAP.md`](COURSE_MAP.md)。

## 运行方式

安装依赖并运行仓库参考实现的验收：

```bash
uv sync
uv run pytest -v
```

第一次学习直接从 Lesson 00 开始：

```bash
uv run python lessons/00_python_foundation/experiments.py
```

完成某一课的 `practice/starter.py` 后，用同一课的测试验收自己的实现：

```bash
uv run pytest lessons/<lesson>/tests -v --learner
```

## 仓库导航

- [`COURSE_MAP.md`](COURSE_MAP.md)：Stage → Lesson 学习路线。
- [`lessons/`](lessons/)：12 节主课程、练习、参考实现与验收测试。
- [`tests/`](tests/)：课程结构和仓库健康检查。
- [`AUTHORING.md`](AUTHORING.md)：课程维护者使用的写作与术语规则；学习者不需要先阅读。
- [`references/`](references/)：历史资料与现代课程的对应关系。
- [`legacy/cloudfit_translation/`](legacy/cloudfit_translation/)：原 BBC R&D Cloudfit 中文翻译与配套资料的归档。
