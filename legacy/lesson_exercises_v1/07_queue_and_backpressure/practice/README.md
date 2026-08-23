# Practice — bounded pipeline

从 AsyncIterable 持续读取 job，通过 bounded Queue 交给固定数量 consumer。source 很快时必须被 queue 反压，而不是全部预读。

验收：`uv run pytest lessons/07_queue_and_backpressure/tests -v --learner`
