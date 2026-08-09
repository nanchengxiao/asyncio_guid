# Practice — downstream capacity

批量处理很多 item，但下游同一时间最多允许 `limit` 个调用。既不能超限，也不能退化成完全串行。

验收：`uv run pytest lessons/06_bounded_concurrency/tests -v --learner`
