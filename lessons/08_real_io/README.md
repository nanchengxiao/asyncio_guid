# Lesson 08 — Real I/O

## 本节目标

学完本节，你应该能够：

- 使用 `aiohttp` 执行真实异步 HTTP
- 把 `ClientSession` 当成有生命周期的资源
- 理解 connection pool 如何限制真实并发
- 编写不依赖公网的网络测试

## 进入本课前

你已经学过 Task、并发、资源容量、timeout、cancellation 和 cleanup。

本课新增：

- **aiohttp**：Python 常用的异步 HTTP 库。
- **`ClientSession`**：一段时间内复用的 HTTP 客户端会话，负责管理请求和连接资源。
- **connector**：aiohttp 中负责底层连接管理的组件。
- **connection pool（连接池）**：管理并复用有限数量连接的资源池。

## 为什么需要学习它

`asyncio.sleep()` 适合学习调度，但真实网络请求还会遇到连接复用、连接数量上限、响应读取和资源关闭。进入工程阶段后，需要把这些真实 I/O 资源放进模型。

## 核心理论

```python
connector = aiohttp.TCPConnector(limit=4)
async with aiohttp.ClientSession(connector=connector) as session:
    ...
```

`ClientSession` 通常应该覆盖一批相关请求，而不是每个请求都重新创建。

`TCPConnector(limit=4)` 表示连接池有明确容量。即使创建 100 个请求 Task，真正能同时占用连接的请求仍然受连接池限制，其余请求要等待可用连接。

```text
很多 request Task
       ↓
connection pool (limit=4)
       ↓
HTTP server
```

数据库连接池也可以用同一个模型理解：

```text
many tasks → finite pool → downstream
```

这里的 response body 指 HTTP 响应中的实际内容；读取它本身也可能是异步 I/O。

课程测试使用本地临时 server，这样可以控制响应、延迟和峰值并发，不依赖公网。

## 脑内执行模型

```text
request A ─┐
request B ─┼─→ ClientSession → pool(limit=4) → local server
request C ─┤
...        ┘
```

## 常见误解

- **误区：** 每个 HTTP 请求都创建一个 `ClientSession` 更安全。这样会失去连接复用并增加额外开销。
- **误区：** async HTTP 没有资源上限。真实连接和服务器容量仍然有限。
- **误区：** 100 个 Task 就一定有 100 个请求同时打到服务器。connection pool 会限制真实连接数量。
- **误区：** 测试 HTTP 必须访问公网。本地 server 更稳定、可控。

## 本节规则总结

1. `ClientSession` 是需要明确关闭的资源。
2. 一批相关请求通常复用一个 Session。
3. connection pool 是并发资源模型的一部分。
4. Task 数量不等于真实连接数量。
5. 真实 I/O 仍要考虑 timeout、cancellation 和 cleanup。

## 关键问题

1. 为什么不推荐每个请求都新建一个 `ClientSession`？
2. connection pool 的 `limit` 限制了什么？
3. 100 个 Task + connector limit=4 时，真实并发为什么不等于 100？
4. 为什么 HTTP 与数据库连接池可以用同一个容量模型理解？
5. 为什么课程测试使用本地 server？

## 场景命题

批量 GET 一组本地 URL，复用一个 `ClientSession`，并让 `TCPConnector` 的 `limit` 成为可配置连接容量。返回 JSON 结果且保持输入顺序。

## 验收

测试会启动本地 aiohttp server，验证响应正确，并确认服务器观测到的峰值 active 请求不超过 connector limit。

仓库参考实现：

```bash
uv run pytest lessons/08_real_io/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/08_real_io/tests -v --learner
```
