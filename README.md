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

`Stage` 表示一段学习主题，不是课次；两个 Lesson 使用同一个 Stage，表示它们共同完成这一阶段。实际学习顺序始终是 Lesson 00 → 11。

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

1. 先读“进入本课前”，再扫读“本课新增术语”；只看这些词分成哪几组，不要求此时记住定义；
2. 读核心例子时先预测输出，再直接运行 `case.py`；
3. 对照“把本课知识点对到代码上”和执行时间线，确认每个术语落在哪一行、等待时谁在运行、失败后谁负责收尾；
4. 再读核心理论、脑内执行模型与常见误解，最后合上讲义回答“关键问题”；
5. 在空白 `practice.py` 中独立完成“场景命题”，卡住时只回看对应知识点或 `case.py`；
6. 最后重新运行自己的实现，用题目要求的输出与边界逐项验收。

不要求一次阅读就记住所有内容。Lesson 00、07、08、11 信息量较大，讲义会给出第一遍通关重点：先跑通核心例子并形成执行模型，再回头补齐术语和细节。能用自己的话回答“脑内执行模型”中的核心问题，就可以先继续下一课；遗忘细节时再回来查。

运行某课的核心示例：

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
