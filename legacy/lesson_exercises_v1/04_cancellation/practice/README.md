# Practice — cancellable upload

分片上传过程中调用方可能取消整个上传。无论完成或取消都必须 cleanup；取消不能被转成“成功”。

验收：`uv run pytest lessons/04_cancellation/tests -v --learner`
