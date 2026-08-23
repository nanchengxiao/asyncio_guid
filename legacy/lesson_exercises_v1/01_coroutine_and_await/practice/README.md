# Practice — order context

订单详情必须先取得 order，随后才能从 `order["customer_id"]` 获取 customer。

TODO 只描述业务目标：保持这个 data dependency，并返回 `{order, customer}`。不要为了“看起来更异步”而提前开始一个还缺少必要输入的工作。

验收：`uv run pytest lessons/01_coroutine_and_await/tests -v --learner`
