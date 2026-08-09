# References

课程主体是 Python 3.11+ 的工程课程，但原仓库的 BBC R&D Cloudfit 中文翻译仍有很高参考价值。旧资料已经统一归档到 [`legacy/cloudfit_translation/`](../legacy/cloudfit_translation/)，这里仅维护“旧资料 → 新课程”的映射。

## 旧资料映射

| 原资料 | 课程中的去向 |
|---|---|
| [`01_基础概念与模式.md`](../legacy/cloudfit_translation/01_基础概念与模式.md) | Coroutine / Event Loop 心智模型被简化后用于 Lesson 01–02；栈帧等底层展开留作参考 |
| [`02_可等待对象_任务与Future.md`](../legacy/cloudfit_translation/02_可等待对象_任务与Future.md) | coroutine object / Task / Future 区分用于 Lesson 01–03；Future 手工操作不作为主线 |
| [`03_异步上下文管理器与异步迭代器.md`](../legacy/cloudfit_translation/03_异步上下文管理器与异步迭代器.md) | 资源生命周期思想贯穿真实 I/O；详细协议留作扩展阅读 |
| [`04_库支持.md`](../legacy/cloudfit_translation/04_库支持.md) | aiohttp 与测试思想进入 Lesson 08；旧生态版本说明留作历史参考 |
| [`05_混合同步与异步代码.md`](../legacy/cloudfit_translation/05_混合同步与异步代码.md) | blocking I/O 与线程桥接进入 Lesson 09；底层 fd / executor 细节降为参考 |

完整旧版入口见 [`legacy/cloudfit_translation/README.md`](../legacy/cloudfit_translation/README.md)。原始来源与许可说明继续保留在归档中的 [`NOTICE.md`](../legacy/cloudfit_translation/NOTICE.md) 与 [`SOURCES.md`](../legacy/cloudfit_translation/SOURCES.md)。
