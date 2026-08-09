# Practice — order context

订单详情必须先取得 order，随后才能从 `order["customer_id"]` 获取 customer。

TODO 只描述业务目标：保持这个数据依赖，并返回 `{order, customer}`。不要提前创建无意义 Task。

验收：`uv run pytest lessons/01_coroutine_and_await/tests -v --learner`
