# Practice — 包装旧同步 SDK

legacy loader 是 synchronous blocking function。批量调用时，Event Loop 仍需响应其他 Task，并限制 worker thread 同时访问 loader 的数量。

验收：`uv run pytest lessons/09_blocking_io/tests -v --learner`
