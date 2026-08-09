# Practice — sibling failure

一个父业务操作拥有多个 worker。任一 worker 失败时，其余 sibling 不应继续孤立运行；它们需要收到取消并执行自己的 cleanup。

验收：`uv run pytest lessons/03_structured_concurrency/tests -v --learner`
