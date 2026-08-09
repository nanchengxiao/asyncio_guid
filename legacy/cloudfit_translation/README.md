# asyncio 中文学习指南

本压缩包根据 BBC R&D Cloudfit 团队发布的五篇 Python `asyncio` 教学页面整理并翻译，保留标题结构、示例代码、重要提示与原文链接。

## 文件目录

- `01_基础概念与模式.md`
- `02_可等待对象_任务与Future.md`
- `03_异步上下文管理器与异步迭代器.md`
- `04_库支持.md`
- `05_混合同步与异步代码.md`
- `asyncio_guide_zh.md`：五篇合并版
- `asyncio_guide_zh.html`：可离线阅读的合并版 HTML
- `assets/SubVsCoRoutines.png`：原文第 1 篇中的子程序/协程对比图
- `SOURCES.md`：五篇原始页面和图示资源地址
- `NOTICE.md`：来源、翻译和许可说明
- `MANIFEST.json`：文件清单及 SHA-256 校验值

## 阅读建议

按 1～5 的顺序阅读：

1. 先建立事件循环、任务和协程的概念模型；
2. 理解 `async def`、`await`、Future 与 Task；
3. 学习 `async with`、`async for` 和异步生成器；
4. 了解 `aiohttp`、`AsyncExitStack`、`AsyncMock` 等常用支持；
5. 掌握同步阻塞库与异步代码混用时的线程池、进程池和文件描述符接口。

## 版本提示

原文包含 Python 3.6～3.10 时代的兼容性与生态说明。译文保留了这些历史上下文，并在少量位置增加提示。实际项目请同时查阅当前 Python 与第三方库的官方文档。

## 运行环境（uv）

使用 [uv](https://docs.astral.sh/uv/) 管理环境与依赖：

```bash
uv sync        # 创建 .venv 并安装依赖（含 aiohttp）
```

`examples/` 下的示例（要求 Python ≥ 3.9）均可直接运行：

```bash
uv run python examples/01_interleave.py
uv run python examples/04_aiohttp_client.py   # 需要联网
uv run python -m unittest examples/06_async_tests.py -v
```
