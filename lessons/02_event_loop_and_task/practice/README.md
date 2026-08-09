# Practice — dashboard concurrency

user 与 orders 只共享输入 user_id，彼此无数据依赖。实现聚合函数，让两个 I/O 等待尽可能重叠，并确保函数返回前所有自己创建的工作已结束。

验收：`uv run pytest lessons/02_event_loop_and_task/tests -v --learner`
