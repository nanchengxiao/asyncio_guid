# Lesson 08 — Real io

## 本节目标

学完本节，你应该能够：

- 使用 aiohttp 执行真实异步 HTTP
- 把 ClientSession/connector 当成资源生命周期
- 理解 connection pool 如何限制并发
- 编写不依赖公网的网络测试

## 为什么需要学习它

`asyncio.sleep()` 可以教学调度，但它不会暴露连接池、socket 生命周期、响应读取和服务器侧并发。进入工程阶段后，需要把真实 I/O 资源放进模型。

## 核心理论

`aiohttp.ClientSession` 应通常拥有比单个请求更长的生命周期。它内部管理连接复用与 connector pool。

```python
connector = aiohttp.TCPConnector(limit=4)
async with aiohttp.ClientSession(connector=connector) as session:
    ...
```

如果创建 100 个请求 Task，而 connector limit=4，真正同时占用连接的请求仍受池容量约束；其余工作在连接池前等待。

数据库连接池遵循同一个资源模型：业务可能有很多 Task，但真正能同时执行 SQL 的数量受 pool size 限制。课程不要求部署真实数据库；你需要形成的模型是 `many tasks → finite pool → downstream`，并知道 pool wait 也应进入 timeout、metrics 与容量规划。

## 脑内执行模型

```text
request tasks (many)
      ↓
TCPConnector pool limit=4
      ↓
local aiohttp test server
```

## 常见误解

- **误区：** 每个 HTTP 请求都新建一个 ClientSession 更安全。反复建 session 会失去连接复用并增加资源开销。
- **误区：** async HTTP 没有资源上限。连接池本身就是容量。
- **误区：** 测试异步 HTTP 必须调用公网。本地 server 更可控、更稳定。
- **误区：** 只要是 aiohttp 就不会超时。时间预算仍需显式设计。

## 本节规则总结

1. Session 生命周期应覆盖一批相关请求。
2. 连接池是并发资源模型的一部分。
3. HTTP body 的读取同样是异步 I/O。
4. 核心课程测试不依赖公网。
5. 真实 I/O 仍要考虑 timeout/cancellation/cleanup。

## 关键问题

1. 为什么不推荐每请求创建一个 ClientSession？
2. 100 个 Task + connector limit=4 时，真实并发大致受什么限制？
3. 连接池限制与应用 Semaphore 有何重叠和差异？
4. 为什么本地 server 比公共测试 API 更适合课程验收？
5. 取消一个正在读 body 的请求时资源谁负责释放？

## 场景命题

批量 GET 一组本地 URL，复用一个 ClientSession，并让 TCPConnector 的 limit 成为可配置资源容量。返回 JSON 列表且保持输入顺序。

## 验收

测试启动本地 aiohttp server，观测峰值 active 请求不超过 connector limit；无需公网。

仓库参考实现：

```bash
uv run pytest lessons/08_real_io/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/08_real_io/tests -v --learner
```
