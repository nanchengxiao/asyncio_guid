# Practice — local HTTP batch

使用 aiohttp 批量 GET URL，复用一个 ClientSession，并让 connector limit 表达连接容量。课程测试会启动本地服务器，不需要公网。

验收：`uv run pytest lessons/08_real_io/tests -v --learner`
