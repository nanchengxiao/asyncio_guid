# asyncio_guid

一套从 asyncio 初学者走向生产级异步工程能力的实践课程。

这不是 asyncio API 百科。课程的目标是让你面对真实业务时，先建立任务、依赖、资源和失败模型，再把模型映射为清晰、可维护、可测试的 asyncio 代码。

## 适合谁

你至少应当：

- 知道 `async def` / `await` 的基本写法；
- 使用过 `asyncio.create_task()` 或 `asyncio.gather()`；
- 愿意从“会调用 API”进一步学习 Task 生命周期、取消、超时、背压与生产级设计。

课程统一使用 **Python >= 3.11**，并优先教授 `TaskGroup`、`asyncio.timeout()` 等现代 asyncio 设计。

## 仓库结构

```text
asyncio_guid/
├── README.md                 # 课程入口
├── COURSE_MAP.md             # Stage → Lesson → 验收地图
├── lessons/                  # 12 节现代 asyncio 主课程
├── tests/                    # 仓库结构健康检查
├── references/               # 旧资料到新课程的映射索引
└── legacy/
    └── cloudfit_translation/ # 原仓库历史资料，自包含归档
```

学习时只需要沿 `README.md` → `COURSE_MAP.md` → `lessons/` 前进。旧版翻译和示例统一收在 `legacy/cloudfit_translation/`，不会与现代课程主线混在一起。

## 学习方式

每节课形成同一个闭环：

```text
理论
  ↓
关键问题
  ↓
场景命题
  ↓
practice/starter.py
  ↓
行为测试验收
```

默认测试验证仓库中的参考实现，因此 clone 后课程仓库本身应保持绿色；当你完成某一课的 starter 后，增加 `--learner` 即可用同一组行为测试验收自己的实现。

## 课程路线

| Stage | Lesson | 核心能力 | 实践场景 |
|---|---|---|---|
| 0 | 00 Python 必要基础 | 暂停、恢复、资源生命周期、finally | 流式读取与可靠关闭 |
| 1 | 01 Coroutine / await | coroutine function/object、真正开始执行的时机 | 订单上下文串行依赖 |
| 2 | 02 Event Loop / Task | Task、调度、真正的并发 | Dashboard 并发取数 |
| 3 | 03 Structured Concurrency | Task ownership、TaskGroup | 一组兄弟任务失败联动 |
| 4 | 04 Cancellation | cancel、CancelledError、cleanup | 可取消的分片上传 |
| 4 | 05 Timeout / Exception | timeout、ExceptionGroup、failure semantics | 多依赖服务调用 |
| 5 | 06 Bounded Concurrency | Semaphore、资源容量 | 限制下游并发访问 |
| 5 | 07 Queue / Backpressure | bounded Queue、producer/consumer | 有背压的数据流水线 |
| 6 | 08 Real I/O | aiohttp、连接池、真实网络 I/O | 本地 HTTP 批量抓取 |
| 6 | 09 Blocking I/O | to_thread、I/O-bound vs CPU-bound | 包装同步遗留 SDK |
| 7 | 10 Business Modeling | 六问模型、DAG、required/optional | Async Service Aggregator |
| 8 | 11 Production Asyncio | shutdown、retry、idempotency、rate limit、observability | Job Processing Service |

更详细的 Stage → Lesson → 验收矩阵见 [`COURSE_MAP.md`](COURSE_MAP.md)。

## 怎么开始

```bash
uv sync
uv run pytest -v
```

完成某一课练习后，例如 Lesson 06：

```bash
uv run pytest lessons/06_bounded_concurrency/tests -v --learner
```

## 每节课怎么学

1. 阅读该 Lesson 的 `README.md`。
2. 遇到代码先不要运行，先预测执行顺序或画时间线。
3. 运行最小实验，核对预测。
4. 不查资料回答“关键问题”。
5. 阅读场景命题与 `practice/README.md`。
6. 完成 `practice/starter.py` 中按业务目标描述的 TODO。
7. 使用 `--learner` 跑该课测试。
8. 最后确认自己不仅知道“怎么写”，还能解释“为什么这样设计”。

## 两套验收

### 仓库健康检查

```bash
uv run pytest -v
```

这会验证课程结构与每节课的参考实现，不会因为 starter 故意留空而失败。

### 学习者练习验收

```bash
uv run pytest lessons/<lesson>/tests -v --learner
```

测试尽量验证行为，而不是搜索 `asyncio.gather`、`Semaphore` 等源码字符串。

## 历史资料

仓库最初是 BBC R&D Cloudfit asyncio 系列五篇中文翻译及配套示例。为了让新课程目录保持清晰，原仓库资料现在统一归档到 [`legacy/cloudfit_translation/`](legacy/cloudfit_translation/)。

归档中保留：

- 原版 `README.md`；
- 五篇中文翻译与合并版 Markdown / HTML；
- 原图片、旧 examples、样式文件；
- 原 `NOTICE.md`、`SOURCES.md`、`MANIFEST.json`；
- 原项目的 `pyproject.toml` 与 `uv.lock`，用于还原当时的运行环境。

归档文件本身尽量保持原样，只改变仓库路径。新课程对这些资料的吸收与取舍见 [`references/README.md`](references/README.md)。来源与许可信息见 [`legacy/cloudfit_translation/NOTICE.md`](legacy/cloudfit_translation/NOTICE.md) 和 [`legacy/cloudfit_translation/SOURCES.md`](legacy/cloudfit_translation/SOURCES.md)。

## 最终能力

完成课程后，你应当能够从业务需求出发完成：

```text
识别工作单元
  ↓
区分 I/O 与 CPU 工作
  ↓
画任务依赖 DAG
  ↓
决定串行 / 并发
  ↓
明确 Task owner 与生命周期
  ↓
确定资源容量与并发上限
  ↓
设计 timeout / cancellation / exception
  ↓
设计 backpressure
  ↓
选择合适 primitive
  ↓
写出可维护、可测试的异步代码
```
