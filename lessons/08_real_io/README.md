# Lesson 08 — 把真实网络连接纳入资源模型

## 进入本课前

你已经学过 Task、concurrency、resource、timeout、cancellation、cleanup、Semaphore 和 bounded concurrency。

## 本课新增术语

- **HTTP**：客户端和服务器之间常用的一套请求/响应规则；客户端发 request，服务器回 response。
- **client（客户端）**：主动向另一端发起请求的一方。
- **server（服务器）**：接收请求、执行处理并返回 response 的一方。
- **request（请求）**：client 发给 server 的一次“请处理这件事”的消息。
- **response（响应）**：server 对一次 request 返回的结果。
- **URL**：告诉 client“要访问哪个网络位置”的地址字符串。
- **JSON**：一种常见文本数据格式，用对象、数组、字符串、数字等结构表示数据。
- **aiohttp**：Python 中常用的异步 HTTP 库。
- **`ClientSession`**：aiohttp 中负责一批相关 HTTP request、并管理底层连接资源的 client 会话对象。
- **connector**：aiohttp 中负责创建、复用和限制底层网络连接的组件。
- **connection pool（连接池）**：保存并复用有限数量连接的资源池；没有可用连接时，新 request 需要等待。
- **`TCPConnector`**：aiohttp 提供的一种 connector；本课只需要知道它的 `limit` 可以限制 connection pool 容量。
- **response body（响应体）**：HTTP response 中真正承载业务内容的那部分数据。

## 本节目标

学完本节，你应该能够：

- 使用 aiohttp 执行真实异步 HTTP request；
- 把 `ClientSession` 当成有生命周期的 resource；
- 理解 connection pool 怎样限制真实网络 concurrency；
- 解释 Task 数量为什么不等于真实连接数量；
- 编写不依赖公网的 HTTP 测试。

## 为什么需要学习它

`asyncio.sleep()` 很适合学习 scheduling，但真实网络调用还会遇到更多资源边界：

- 连接要创建和关闭；
- 连接可以复用；
- 同时可用的连接数量有限；
- response body 的读取本身也可能需要等待；
- server 自己也有容量。

进入真实 I/O 后，不能再把“网络等待”简单想成一个 `sleep()`。

## 核心理论

### 1. `ClientSession` 是需要管理生命周期的 resource

```python
connector = aiohttp.TCPConnector(limit=4)

async with aiohttp.ClientSession(connector=connector) as session:
    ...
```

这里的 `async with` 可以先类比 Lesson 00 的 `with`：

```text
进入
  ↓
获得可用 session
  ↓
执行一批 request
  ↓
退出
  ↓
关闭 session 及相关连接资源
```

本课不要求系统学习“异步 context manager”的所有细节，只需要先把它看成：

> 与 `with` 类似，但进入或退出资源时本身也可能需要等待。

这句话就是本课第一次用到“异步 context manager”的含义。

### 2. 一批相关 request 通常复用一个 Session

不要机械地每个 request 都新建：

```python
async with aiohttp.ClientSession() as session:
    ...
```

然后下一次 request 又重新创建新的 Session。

`ClientSession` 的一个重要价值就是在一批相关 request 之间复用连接和客户端资源。

可以把它理解成：

```text
很多 request
    ↓
同一个 ClientSession
    ↓
复用有限连接
```

### 3. Connection pool 是真实的容量边界

```python
connector = aiohttp.TCPConnector(limit=4)
```

这里 `limit=4` 表示：connector 管理的连接池同时最多允许有限数量连接被占用。

即使创建了 100 个 request Task，也不意味着 100 个 request 能同时占住 100 条连接。

```text
100 个 request Task
        ↓
connection pool (limit=4)
        ↓
最多少量真实连接同时工作
        ↓
其余 request 等待连接可用
```

这和 Lesson 06 的 Semaphore 模型很像：

```text
很多工作 → 有限通行证 → 稀缺资源
```

这里只是“通行证”由真实 connection pool 管理。

### 4. 读取 response body 也可能是异步 I/O

发出 request 后得到 response，不代表所有响应内容已经完整进入内存。

例如：

```python
async with session.get(url) as response:
    data = await response.json()
```

这里：

- `session.get(url)` 发起 HTTP request；
- `response` 表示 HTTP response；
- `await response.json()` 读取 response body，并把 JSON 内容转换成 Python 数据结构。

网络数据可能还在到达，所以读取 body 仍然可能需要等待。

### 5. 为什么测试使用本地 server

课程测试会在本机启动一个临时 HTTP server。

这样可以自己控制：

- 每个 response 返回什么；
- 每次 request 故意等待多久；
- server 同时看到了多少 active request；
- 测试是否稳定重复。

如果测试依赖公网，网络波动、DNS、远端限流或第三方服务故障都会让验收变得不可靠。

### 6. HTTP 与其他连接型资源可以共享同一个模型

虽然本课使用 HTTP，但资源模型可以抽象成：

```text
many Task
   ↓
finite connection pool
   ↓
downstream
```

以后遇到其他有连接数量上限的外部系统，也可以先问：

> 真正有限的连接资源在哪里？谁拥有它？容量是多少？

## 脑内执行模型

```text
request A ─┐
request B ─┼─→ ClientSession → connection pool(limit=4) → local server
request C ─┤
...        ┘
```

其中：

```text
Task 数量             → 代码层面有多少异步工作
connection pool limit → 真实连接资源允许多少同时占用
server active         → 下游实际观察到多少正在处理的 request
```

三者不是同一个数量。

## 常见误解

- **误区：** 每个 HTTP request 都新建一个 `ClientSession` 更安全。  
  **更准确：** 这样会失去连接复用，并增加额外资源开销。

- **误区：** Async HTTP 没有资源上限。  
  **更准确：** 真实连接和 server 容量仍然有限。

- **误区：** 100 个 Task 就一定有 100 个 request 同时打到 server。  
  **更准确：** connection pool 会限制真实连接数量。

- **误区：** 拿到 response 对象就代表 body 已经完整读完。  
  **更准确：** 读取 response body 本身也可能需要异步等待。

- **误区：** HTTP 测试必须访问公网。  
  **更准确：** 本地 server 更稳定，也更容易测量 active request。

## 本节规则总结

1. HTTP 是 request / response 规则；URL 表示访问地址；JSON 是常见数据格式。
2. `ClientSession` 是需要明确关闭的 resource。
3. 一批相关 request 通常复用同一个 Session。
4. Connector 管理底层连接，connection pool 表达有限连接容量。
5. Task 数量不等于真实连接数量。
6. 读取 response body 仍可能是异步 I/O。
7. 网络测试优先使用本地可控 server，而不是依赖公网。

## 关键问题

1. HTTP request 与 response 分别是什么？
2. URL 和 JSON 分别表达什么？
3. `ClientSession` 为什么是 resource？
4. 为什么不推荐每个 request 都新建一个 `ClientSession`？
5. connector 与 connection pool 分别负责什么？
6. `TCPConnector(limit=4)` 的 4 表达什么容量？
7. 100 个 Task + connection pool limit=4 时，真实网络 concurrency 为什么不等于 100？
8. 为什么读取 response body 仍可能需要 `await`？
9. 为什么课程测试使用本地 server？

## 场景命题

批量 GET 一组本地 URL。

要求：

- 使用 aiohttp；
- 一批 request 复用一个 `ClientSession`；
- `TCPConnector` 的 `limit` 可配置；
- 每个 response 读取 JSON body；
- 返回结果顺序与输入 URL 顺序一致；
- 测试不依赖公网。

## 验收

测试会启动本地 aiohttp server，并验证：

- JSON 结果正确；
- 输入顺序被保留；
- server 观察到的 active request 峰值不超过 connector limit；
- Session 和相关资源被正常关闭；
- 测试过程不访问公网。

仓库参考实现：

```bash
uv run pytest lessons/08_real_io/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/08_real_io/tests -v --learner
```
