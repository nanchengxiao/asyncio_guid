# asyncio_guid

## 课程定位

一套面向**已有普通 Python 基础、但可以完全没有 asyncio 基础**的实践课程。

课程从“代码什么时候真正执行、等待时发生什么”开始，逐步走到与外部程序交换真实数据、梳理业务依赖，以及长期运行程序的停止与恢复。重点不是记函数名和调用写法，而是理解执行过程并完成可测试的练习。

课程统一使用 **Python >= 3.11**。

## 前置要求

开始课程前，只要求你已经会普通 Python 的这些内容：

- 变量、函数、参数与返回值；
- `if` / `for` / `while`；
- list / dict 等常见容器；
- 基本的模块导入；
- 知道异常是什么，并见过 `try / except`。

除此之外不要求提前学过本课程的后续内容。

## 学习路线

| Stage | Lesson | 这一课解决的问题 |
|---|---|---|
| 0 | [Lesson 00](lessons/00_python_foundation/00_python_foundation.md) | 补齐逐项读取、暂停后继续、以及可靠收尾所需的 Python 基础 |
| 1 | [Lesson 01](lessons/01_coroutine_and_await/01_coroutine_and_await.md) | 理解“调用一份工作”和“它真正开始执行”为什么可能不是同一时刻 |
| 2 | [Lesson 02](lessons/02_event_loop_and_task/02_event_loop_and_task.md) | 一份工作等待时，怎样让另一份彼此独立的工作继续推进 |
| 3 | [Lesson 03](lessons/03_structured_concurrency/03_structured_concurrency.md) | 让一组子工作有明确负责人，并保证父工作结束前它们已经结束 |
| 4 | [Lesson 04](lessons/04_cancellation/04_cancellation.md) | 正确响应“停止这份工作”的要求，并保证收尾动作仍然发生 |
| 4 | [Lesson 05](lessons/05_timeout_and_errors/05_timeout_and_errors.md) | 给等待设置时间上限，并区分不同失败结果应怎样影响业务 |
| 5 | [Lesson 06](lessons/06_bounded_concurrency/06_bounded_concurrency.md) | 限制同一时刻真正占用有限东西的工作数量 |
| 5 | [Lesson 07](lessons/07_queue_and_backpressure/07_queue_and_backpressure.md) | 限制等待中的工作数量，并在处理不过来时让产生工作的一侧自动放慢 |
| 6 | [Lesson 08](lessons/08_real_io/08_real_io.md) | 程序真正与另一端交换数据时，怎样把有限容量也纳入设计 |
| 6 | [Lesson 09](lessons/09_blocking_io/09_blocking_io.md) | 一个普通函数要等待很久时，怎样避免其他工作也被迫停住 |
| 7 | [Lesson 10](lessons/10_business_modeling/10_business_modeling.md) | 先画清业务步骤谁依赖谁，再决定每份工作最早何时可以开始 |
| 8 | [Lesson 11](lessons/11_production_asyncio/11_production_asyncio.md) | 把停止、失败恢复、重复处理保护和运行状态记录组合进长期运行程序 |

更紧凑的 Stage → Lesson 路线图见 [`COURSE_MAP.md`](COURSE_MAP.md)。

## 运行方式

安装依赖：

```bash
uv sync
```

每节课的目录固定包含三个文件：

| 文件 | 作用 |
|---|---|
| `<课程名>.md` | 本课理论知识讲义 |
| `case.py` | 讲义中核心示例的可运行代码，单独复制出去也能直接运行 |
| `practice.py` | 空文件，留给学习者动手实现 |

推荐学习方式：

1. 通读本课的 `<课程名>.md`；
2. 在 `practice.py` 里照着 `case.py` 亲手写一遍，边写边思考；
3. 卡住了再瞄一眼 `case.py`；
4. 想确认示例的真实输出时，直接运行它：

```bash
uv run python lessons/<lesson>/case.py
```

## 仓库导航

- [`COURSE_MAP.md`](COURSE_MAP.md)：Stage → Lesson 学习路线。
- [`lessons/`](lessons/)：12 节主课程，每课包含讲义、`case.py` 与 `practice.py`。
- [`AUTHORING.md`](AUTHORING.md)：课程维护者使用的写作规范；学习者不需要先阅读。
- [`references/`](references/)：历史资料与现代课程的对应关系。
- [`legacy/cloudfit_translation/`](legacy/cloudfit_translation/)：原 BBC R&D Cloudfit 中文翻译与配套资料的归档。
- [`legacy/lesson_exercises_v1/`](legacy/lesson_exercises_v1/)：旧版练习体系（starter / reference / 验收测试）的归档，仅作历史参考。
