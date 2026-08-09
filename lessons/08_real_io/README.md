# Lesson 08 — 让程序真正和另一端交换数据时也遵守 resource 上限

## 进入本课前

你已经学过 Task、concurrency、resource、timeout、cancellation、cleanup、Semaphore、bounded concurrency、downstream 和 peak。

## 本课新增术语

- **network（网络）**：让不同程序之间可以跨进程或跨机器交换数据的通信环境。
- **client（客户端）**：主动向另一端发送消息、并等待对方返回结果的一方。
- **server（服务器）**：接收另一端发来的消息、执行处理并返回结果的一方。
- **request（请求）**：client 发给 server 的一次“请处理这件事”的消息。
- **response（响应）**：server 针对一次 request 返回的结果。
- **HTTP**：client 和 server 之间常用的一套 request / response 规则。
- **URL**：告诉 client“要访问哪个 network 位置”的地址字符串。
- **JSON**：一种常见文本数据格式，用对象、数组、字符串、数字等结构表示数据。
- **GET**：HTTP request 的一种类型，通常用来获取指定 URL 的内容。
- **connection（连接）**：client 与 server 之间可以用来传输数据的一条通信通道。
- **TCP**：一种常见的 network 传输方式；本课不要求学习协议细节，只需要知道 aiohttp 的 `TCPConnector` 管理这类 connection。
- **aiohttp**：Python 中常用的 async HTTP 库。
- **`ClientSession`**：aiohttp 中负责一批相关 HTTP request、并管理底层 connection resource 的 client 会话对象。
- **connector**：aiohttp 中负责创建、复用和限制底层 connection 的组件。
- **connection pool（连接池）**：保存并复用有限数量 connection 的 resource 池；没有可用 connection 时，新 request 需要等待。
- **`TCPConnector`**：aiohttp 提供的一种 connector；本课只需要知道它的 `limit` 可以限制 connection pool 容量。
- **async context manager（异步上下文管理器）**：像 Lesson 00 的 context manager 一样管理进入和退出，但进入或退出阶段本身允许等待 async 操作。
- **response body（响应体）**：HTTP response 中真正承载业务内容的那部分数据。

## 本节目标

学完本节，你应该能够：

- 使用 aiohttp 执行真实 HTTP request；
- 把 `ClientSession` 当成有 lifecycle 的 resource；
- 理解 connection pool 怎样限制真实 network concurrency；
- 解释 Task 数量为什么不等于真实 connection 数量；
- 使用 async context manager 管理 network resource；
- 编写不依赖外部网站的 HTTP 测试。

## 为什么需要学习它

`asyncio.sleep()` 很适合学习 scheduling，但真实 network 调用还会遇到更多 resource 边界：

- connection 要创建和关闭；
- connection 可以复用；
- 同时可用的 connection 数量有限；
- response body 的读取本身也可能需要等待；
- server 自己也有容量。

进入真实 I/O 后，不能再把“等待外部数据”简单想成一个 `sleep()`。

## 核心理论

### 1. `ClientSession` 是需要管理 lifecycle 的 resource

```python
connector = aiohttp.TCPConnector(limit=4)

async with aiohttp.ClientSession(connector=connector) as session:
    ...
```

这里的 `async with` 使用 async context manager。

可以先类比 Lesson 00 的 `with`：

```text
进入
  ↓
获得可用 session
  ↓
执行一批 request
  ↓
退出
  ↓
关闭 session 及相关 connection resource
```

差别只是：进入或退出这段 resource lifecycle 时，本身也允许发生 async 等待。

### 2. 一批相关 request 通常复用一个 `ClientSession`

不要机械地每个 request 都新建一个 `ClientSession`，然后下一次 request 又重新创建。

`ClientSession` 的一个重要价值就是在一批相关 request 之间复用 connection 和 client resource。

```text
很多 request
    ↓
同一个 ClientSession
    ↓
复用有限 connection
```

### 3. Connection pool 是真实的容量边界

```python
connector = aiohttp.TCPConnector(limit=4)
```

这里 `limit=4` 表示：connector 管理的 connection pool 同时最多允许有限数量 connection 被占用。

即使创建了 100 个 request Task，也不意味着 100 个 request 能同时占住 100 条 connection。

```text
100 个 request Task
        ↓
connection pool (limit=4)
        ↓
最多少量真实 connection 同时工作
        ↓
其余 request 等待 connection 可用
```

这和 Lesson 06 的 Semaphore 模型很像：

```text
很多工作 → 有限通行证 → 稀缺 resource
```

这里只是“通行证”由真实 connection pool 管理。

### 4. GET request 与 response body

课程 practice 会批量 GET 一组本地 URL。

```python
async with session.get(url) as response:
    data = await response.json()
```

这里：

- `session.get(url)` 发起一个 GET request；
- `response` 表示 server 返回的 HTTP response；
- `await response.json()` 读取 response body，并把 JSON 内容转换成 Python 数据结构。

拿到 response 对象，不代表 body 已经完整读入内存。network 数据可能还在到达，所以读取 body 仍然可能需要等待。

### 5. 为什么测试使用本地 server

课程测试会在当前机器上启动一个临时 HTTP server。

这样可以自己控制：

- 每个 response 返回什么；
- 每次 request 故意等待多久；
- server 同时看到了多少 active request；
- 测试是否稳定重复。

如果测试依赖外部网站，network 波动、外部地址暂时不可用、rate limit 或第三方程序故障都会让验收变得不可靠。

### 6. HTTP 与其他 connection resource 可以共享同一个模型

虽然本课使用 HTTP，但 resource 模型可以抽象成：

```text
many Task
   ↓
数量有限的 connection pool
   ↓
downstream
```

图里的 `many` 只表示“很多”，不是新的机制。

以后遇到其他有 connection 数量上限的外部系统，也可以先问：

> 真正有限的 connection resource 在哪里？谁拥有它？容量是多少？

## 脑内执行模型

```text
request A ─┐
request B ─┼─→ ClientSession → connection pool(limit=4) → 本地 server
request C ─┤
...        ┘
```

其中：

```text
Task 数量             → 代码层面有多少 async 工作
connection pool limit → 真实 connection resource 允许多少同时占用
server active         → downstream 实际观察到多少正在处理的 request
```

三者不是同一个数量。

## 常见误解

- **误区：** 每个 HTTP request 都新建一个 `ClientSession` 更安全。  
  **更准确：** 这样会失去 connection 复用，并增加额外 resource 开销。

- **误区：** Async HTTP 没有 resource 上限。  
  **更准确：** 真实 connection 和 server 容量仍然有限。

- **误区：** 100 个 Task 就一定有 100 个 request 同时打到 server。  
  **更准确：** connection pool 会限制真实 connection 数量。

- **误区：** 拿到 response 对象就代表 body 已经完整读完。  
  **更准确：** 读取 response body 本身也可能需要 async 等待。

- **误区：** HTTP 测试必须访问外部网站。  
  **更准确：** 本地 server 更稳定，也更容易测量 active request。

## 本节规则总结

1. Network 让不同程序交换数据；client 发 request，server 回 response。
2. HTTP 是常见的 request / response 规则；URL 表示访问地址；JSON 是常见数据格式；GET 是常见 request 类型。
3. Connection 是 client 与 server 之间的数据通道；connection pool 管理有限 connection 容量。
4. `ClientSession` 是需要明确关闭的 resource，一批相关 request 通常复用同一个 Session。
5. Connector 管理底层 connection，`TCPConnector(limit=...)` 表达 connection pool 上限。
6. Async context manager 允许进入和退出 resource 时发生 async 等待。
7. Task 数量不等于真实 connection 数量。
8. 读取 response body 仍可能是 async I/O。
9. Network 测试优先使用本地可控 server，而不是依赖外部网站。

## 关键问题

1. network 在本课里是什么意思？
2. client 与 server 分别是什么？
3. HTTP request 与 response 分别是什么？
4. URL 和 JSON 分别表达什么？
5. GET request 在本课里做什么？
6. connection 与 connection pool 分别是什么？
7. `ClientSession` 为什么是 resource？
8. 为什么不推荐每个 request 都新建一个 `ClientSession`？
9. connector 与 `TCPConnector` 分别负责什么？
10. `TCPConnector(limit=4)` 的 4 表达什么容量？
11. async context manager 与普通 context manager 的关键差别是什么？
12. 100 个 Task + connection pool limit=4 时，真实 network concurrency 为什么不等于 100？
13. 为什么读取 response body 仍可能需要 `await`？
14. 为什么课程测试使用本地 server？

## 场景命题

批量 GET 一组本地 URL。

要求：

- 使用 aiohttp；
- 一批 request 复用一个 `ClientSession`；
- `TCPConnector` 的 `limit` 可配置；
- 每个 response 读取 JSON body；
- 返回结果顺序与输入 URL 顺序一致；
- 测试不依赖外部网站。

## 验收

测试会启动本地 aiohttp server，并验证：

- JSON 结果正确；
- 输入顺序被保留；
- server 观察到的 active request peak 不超过 connector limit；
- Session 和相关 resource 被正常关闭；
- 测试过程不访问外部网站。

仓库参考实现：

```bash
uv run pytest lessons/08_real_io/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/08_real_io/tests -v --learner
```
