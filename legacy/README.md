# Legacy materials

这里集中存放仓库重构前的历史资料，避免旧版翻译、示例和现代课程主线混在根目录。

## `cloudfit_translation/`

`cloudfit_translation/` 是原仓库内容的自包含归档，主要包括：

```text
cloudfit_translation/
├── README.md
├── 01_基础概念与模式.md
├── 02_可等待对象_任务与Future.md
├── 03_异步上下文管理器与异步迭代器.md
├── 04_库支持.md
├── 05_混合同步与异步代码.md
├── asyncio_guide_zh.md
├── asyncio_guide_zh.html
├── assets/
├── examples/
├── NOTICE.md
├── SOURCES.md
├── MANIFEST.json
├── style.css
├── pyproject.toml
└── uv.lock
```

这些文件用于追溯原始翻译、历史版本 API 说明、旧示例以及 attribution。除路径迁移外，归档内容本身不作为现代课程主线继续维护。

现代学习请从仓库根 [`README.md`](../README.md) 和 [`lessons/`](../lessons/) 开始。需要理解旧资料如何映射到新课程时，查看 [`references/README.md`](../references/README.md)。
