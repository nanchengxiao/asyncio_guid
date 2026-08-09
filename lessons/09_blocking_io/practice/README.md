# Practice — legacy sync SDK bridge

legacy loader 是同步阻塞函数。批量调用时 event loop 仍需响应其他 Task，并限制线程侧同时访问 loader 的数量。

验收：`uv run pytest lessons/09_blocking_io/tests -v --learner`
