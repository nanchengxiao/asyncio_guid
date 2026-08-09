# Lesson 08 — Real I/O

## 本节目标

学完本节，你应该能够：

- 使用 `aiohttp` 执行真实异步 HTTP
- 理解 `ClientSession` 为什么应该被当成一个有生命周期的资源
- 理解 connection pool（连接池）如何限制真实并发
- 编写不依赖公网的异步网络测试

## 进入本课前

你已经学过：Task、并发、timeout、cancellation、Semaphore、bounded Queue 和资源容量。

这一课新增 **aiohttp、ClientSession、connector、connection pool**。

## 为什么需要学习它

前面的课程常用 `asyncio.sleep()` 模拟等待。它很适合学习调度，但真实网络请求还会遇到：

- TCP 连接需要建立和复用；
- 同时可用连接数量有限；
- 响应 body 需要异步读取；
- Client 本身也需要关闭。

所以这一课把“模拟等待”换成真实 HTTP I/O。

## 核心理论

### 1. `aiohttp` 是什么

`aiohttp` 是 Python 常用的异步 HTTP 库。课程只使用它的客户端部分：发送 HTTP 请求并异步等待响应。

### 2. `ClientSession` 是什么

`aiohttp.ClientSession` 可以理解成：

> 一段时间内复用的 HTTP 客户端会话，它负责管理连接、请求相关资源和连接复用。

通常不要为每一个请求都新建一个 Session。

```python
async with aiohttp.ClientSession() as session:
    ...
```

这里的 `async with` 和 Lesson 00 的 `with` 使用同一个资源生命周期思想，只是进入/退出过程本身也可能需要异步等待。

### 3. connector 是什么

`connector` 是 `aiohttp` 中负责底层连接管理的组件。

```python
connector = aiohttp.TCPConnector(limit=4)
```

这里的 `limit=4` 表示连接池的总连接容量上限之一。

### 4. connection pool 是什么

**connection pool（连接池）**可以理解成：

> 提前管理一批可复用连接，让多个请求共享，而不是每次都无条件新建连接。

```text
很多 request Task
       ↓
connection pool，limit=4
       ↓
最多有限数量的真实连接
       ↓
HTTP server
```

所以即使创建了 100 个请求 Task，也不代表会有 100 个请求同时占用网络连接。

这和 Lesson 06 的资源容量模型完全一致：

```text
many tasks → finite resource pool → downstream
```

数据库连接池也是同一个模型：Task 可以很多，但真正能同时使用数据库连接的工作数量有限。

### 5. 为什么 Session 要复用

如果每次请求都创建新的 Session：

```python
async with aiohttp.ClientSession() as session:
    await session.get(...)
```

然后立刻关闭，就很难充分利用连接复用，还会增加额外资源开销。

通常更合理的是“一批相关请求共用一个 Session”。

### 6. 为什么测试用本地 server

课程测试会在本机启动一个临时 HTTP server。

这样可以控制：

- 响应内容；
- 响应延迟；
- 同时正在处理多少请求；
- 是否出现超时。

相比调用公共网站，这种测试更稳定，也不依赖网络环境。

## 脑内执行模型

```text
request Task A ─┐
request Task B ─┼─→ ClientSession → connection pool(limit=4) → local server
request Task C ─┤
...             ┘
```

## 常见误解

- **误区：每个 HTTP 请求都创建一个 `ClientSession` 更安全。** 通常应复用 Session，让连接也能复用。
- **误区：async HTTP 没有资源上限。** 真实连接、文件描述符和服务器容量都有限。
- **误区：100 个 Task 就一定有 100 个请求同时打到服务器。** connection pool 等资源边界会限制真实并发。
- **误区：测试 HTTP 必须访问公网。** 本地 server 更适合可重复的行为测试。

## 本节规则总结

1. `ClientSession` 是需要明确关闭的资源。
2. 一批相关请求通常复用一个 Session。
3. connection pool 是真实资源容量的一部分。
4. Task 数量不等于真实连接数量。
5. 真实 I/O 仍要考虑 timeout、cancellation 和 cleanup。

## 关键问题

1. `ClientSession` 为什么不只是一个“发送请求的函数”？
2. 为什么不推荐每个请求都新建一个 Session？
3. connection pool 的 `limit` 限制了什么？
4. 100 个 Task + connector limit=4 时，为什么真实网络并发不会简单等于 100？
5. 为什么数据库连接池和 HTTP 连接池可以用同一个容量模型理解？
6. 为什么课程测试使用本地 server 而不是公共测试 API？

## 场景命题

批量 GET 一组本地 URL。复用一个 `ClientSession`，并让 `TCPConnector` 的 `limit` 成为可配置的连接容量。

返回 JSON 结果，并保持与输入 URL 相同的顺序。

## 验收

测试会启动本地 aiohttp server，验证响应正确，并观察服务器侧的峰值 active 请求没有超过 connector limit。测试不依赖公网。

仓库参考实现：

```bash
uv run pytest lessons/08_real_io/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/08_real_io/tests -v --learner
```
