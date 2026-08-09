# Practice — Async Service Aggregator

先完成 DESIGN.md，再编码。user/orders required 且第一层并发；account 依赖 user 且 required；recommendations 依赖 orders 且 optional。

验收：`uv run pytest lessons/10_business_modeling/tests -v --learner`
