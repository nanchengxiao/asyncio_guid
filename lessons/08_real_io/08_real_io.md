# Lesson 08 — 让程序真正和另一端交换数据时也遵守 resource 上限

## 进入本课前

你已经学过 Task、concurrency、resource、timeout、cancellation、cleanup、Semaphore、bounded concurrency、downstream、peak、async generator、`async with` 和 async context manager。

第一遍阅读时，先把“在本机启动另一端程序”的代码当作准备好的实验支架，不要求记住它的写法。把注意力放在发出请求的一侧：一批请求复用同一个对象、实际通信数量有明确上限、错误结果会被拒绝、返回数据会被完整读取。理解这条主线后，再回头阅读实验支架怎样启动和关闭。

## 本课新增术语

这一课的词比较多，不需要先背完。先按“HTTP 交换 → client resource → 本地 server 测试支架”三组建立位置感，下一节会把每个词全部对到同一段代码上。

**第一组：读懂一次 HTTP 交换**

- **network（网络）**：让不同程序之间可以跨进程或跨机器交换数据的通信环境。
- **client（客户端）**：主动向另一端发送消息、并等待对方返回结果的一方。
- **server（服务器）**：接收另一端发来的消息、执行处理并返回结果的一方。
- **request（请求）**：client 发给 server 的一次“请处理这件事”的消息。
- **response（响应）**：server 针对一次 request 返回的结果。
- **handler（处理函数）**：server 每收到一个匹配的 request 时调用的 async 函数；它负责构造这次 response。
- **HTTP**：client 和 server 之间常用的一套 request / response 规则。
- **URL**：告诉 client“要访问哪个 network 位置”的地址字符串。
- **`127.0.0.1`**：只指向当前这台机器自身的 network 地址；本例用它让 client 访问同一进程临时启动的本地 server。
- **port（端口）**：network 地址中的一个数字，用来进一步指定当前机器上的哪一个 server 入口接收连接。
- **JSON**：一种常见文本数据格式，用对象、数组、字符串、数字等结构表示数据。
- **GET**：HTTP request 的一种类型，通常用来获取指定 URL 的内容。
- **HTTP status code（HTTP 状态码）**：server 放在 response 中的数字结果分类；例如 2xx 通常表示成功，4xx / 5xx 表示 client 或 server 一侧出现错误。
- **`response.raise_for_status()`**：检查 response status；遇到 4xx / 5xx 时抛出异常，避免把错误 response 当成正常业务结果继续处理。
- **response body（响应体）**：HTTP response 中真正承载业务内容的那部分数据。
- **connection（连接）**：client 与 server 之间可以用来传输数据的一条通信通道。
- **TCP**：HTTP 常用的一种底层 network 传输方式；本课不要求学习它的协议细节。

**第二组：管理 aiohttp client resource**

- **aiohttp**：Python 中常用的 async HTTP 库。
- **`ClientSession`**：aiohttp 中负责一批相关 HTTP request、并管理底层 connection resource 的 client 会话对象。
- **connector**：aiohttp 中负责创建、复用和限制底层 connection 的组件。
- **connection pool（连接池）**：保存并复用有限数量 connection 的 resource 池；没有可用 connection 时，新 request 需要等待。
- **`TCPConnector`**：aiohttp 提供的一种 connector；本课只需要知道它的 `limit` 可以限制 connection pool 容量。

**第三组：建立可控的本地 server 测试支架**

- **`@asynccontextmanager`**：`@contextmanager` 的 async 版本；它把一个只 `yield` 一次的 async generator function 包装成 async context manager，让进入或退出阶段可以使用 `await`。
- **route（路由规则）**：把一种 HTTP request 与对应 handler 连接起来的匹配规则；本例把任意 GET path 交给同一个 handler。
- **`web.Application`**：aiohttp server 端保存 route 等配置的应用对象；本课只把它用于可控测试支架。
- **`web.AppRunner`**：负责准备、运行并 cleanup 一个 `web.Application` 的对象。
- **`web.TCPSite`**：把 runner 绑定到指定地址和 port、真正开始接收 TCP connection 的对象。

## 一个例子串起全部术语

下面用 `local_server()` 在本机临时启动一个 HTTP server，再由 client 发出 6 个 GET request。代码创建了 6 个 Task，但 connection pool 只允许 2 条 connection 同时工作，因此可以直接观察“Task 数量”和“真实 network 容量”不是一回事。Local server 是为了稳定实验而准备的测试支架，同时也示范怎样让 server 与 client 各自拥有清楚的 resource lifecycle；第一次运行时可以先把这部分当作已经准备好的实验环境。代码就是本课的 `case.py`：

```python
import asyncio
from contextlib import asynccontextmanager

from aiohttp import ClientSession, TCPConnector, web

@asynccontextmanager
async def local_server():
    """本地临时 server：不依赖外部网站，方便观察 active request。"""
    stats = {"active": 0, "peak": 0}

    async def handler(request):
        stats["active"] += 1
        stats["peak"] = max(stats["peak"], stats["active"])
        try:
            await asyncio.sleep(0.1)           # server 处理 request 也需要时间
            return web.json_response({"path": request.path})
        finally:
            stats["active"] -= 1              # 失败或 cancellation 时也修正观测值

    app = web.Application()
    app.router.add_get("/{path:.*}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        site = web.TCPSite(runner, "127.0.0.1", 0)  # 0：让系统分配可用端口
        await site.start()
        port = runner.addresses[0][1]
        yield port, stats                      # server 已可用，交给 client 测试
    finally:
        await runner.cleanup()                 # 启动后任一路径都停止本地 server
        print("local server cleanup：完成")

async def fetch_one(session, url):
    # 拿到 response 不代表 body 已读完；读取 body 本身也可能需要等待
    async with asyncio.timeout(1.0):            # 复用 Lesson 05 的 time budget
        async with session.get(url) as response:
            response.raise_for_status()         # 4xx / 5xx 不能伪装成成功结果
            data = await response.json()
    return url, data

async def main():
    async with local_server() as (port, server_stats):
        urls = [f"http://127.0.0.1:{port}/data/{number}" for number in range(6)]
        connector = TCPConnector(limit=2)       # connection pool 的容量边界
        # 一批相关 request 复用同一个 ClientSession，由它复用有限 connection
        async with ClientSession(connector=connector) as session:
            async with asyncio.TaskGroup() as tg:
                tasks = [tg.create_task(fetch_one(session, url)) for url in urls]
            results = [task.result() for task in tasks]  # 与输入 URL 顺序一致
        for url, data in results:
            print(url, data)
        print(f"server 观察到同时处理的 request 峰值 = {server_stats['peak']}"
              f"（connection pool limit=2，远少于 Task 数量）")

asyncio.run(main())
```

一次运行的输出结构如下；`<port>` 会替换成系统当时分配的数字：

```text
http://127.0.0.1:<port>/data/0 {'path': '/data/0'}
http://127.0.0.1:<port>/data/1 {'path': '/data/1'}
http://127.0.0.1:<port>/data/2 {'path': '/data/2'}
http://127.0.0.1:<port>/data/3 {'path': '/data/3'}
http://127.0.0.1:<port>/data/4 {'path': '/data/4'}
http://127.0.0.1:<port>/data/5 {'path': '/data/5'}
server 观察到同时处理的 request 峰值 = 2（connection pool limit=2，远少于 Task 数量）
local server cleanup：完成
```

把本课知识点对到代码上：

| 术语或知识点 | 在这个例子里指什么 |
| --- | --- |
| **network** | ClientSession 与本地 server 通过 `127.0.0.1` 地址交换数据；通信没有离开当前机器，但仍走真实 network I/O |
| **client** | `ClientSession` 这一侧主动发出 request 并等待结果 |
| **server** | `web.Application()`、`handler()` 和启动后的 `site` 组成接收 request 的一侧 |
| **handler** | 每个 GET 到达后调用内部的 `handler(request)`；它等待约 0.1 秒并构造 JSON response |
| **request** | `session.get(url)` 发出的每一次处理请求；server 端的 `handler(request)` 接收它 |
| **response** | `web.json_response(...)` 由 server 返回，client 端通过 `response` 变量读取 |
| **HTTP** | URL 以 `http://` 开头，client 与 server 按 HTTP 的 request / response 方式通信 |
| **URL** | `urls` 中每个字符串指定本地 server 的地址与 `/data/<数字>` 路径 |
| **`127.0.0.1`** | URL 和 `TCPSite` 都使用这个地址，因此 client 与 server 通信始终留在当前机器 |
| **port** | `runner.addresses[0][1]` 取得系统分配的数字，再嵌入每个 URL；实际运行时它会变化 |
| **JSON** | Server 用 `web.json_response()` 发送 JSON，client 用 `response.json()` 转成 Python 数据 |
| **GET** | `app.router.add_get(...)` 接收 GET，`session.get(url)` 发出 GET |
| **HTTP status code** | 本地 handler 正常返回 2xx；`response.raise_for_status()` 明确检查 status，4xx / 5xx 会转成失败路径 |
| **connection** | Client 与 server 之间实际传输 request 和 response 的通信通道 |
| **TCP** | `TCPConnector` 管理 aiohttp 使用的 TCP connection；本课不展开传输协议细节 |
| **aiohttp** | `ClientSession`、`TCPConnector` 和 `web` 都来自这个 async HTTP 库 |
| **route / server 测试支架** | `app.router.add_get(...)` 把 GET path 交给 handler；`web.AppRunner` 管理 lifecycle，`web.TCPSite` 在本地地址和 port 上接收连接 |
| **`ClientSession`** | 六个相关 request 共用的 client 会话，同时负责相关 connection 的 lifecycle |
| **connector** | `connector` 变量负责管理、复用并限制底层 connection |
| **connection pool** | `TCPConnector(limit=2)` 提供的有限 connection 容量；六个 Task 要通过这里取得通信通道 |
| **`TCPConnector`** | 具体创建 connection pool 的 aiohttp 组件，`limit=2` 写明容量 |
| **async context manager** | `local_server()`、`ClientSession(...)` 和 `session.get(...)` 分别管理 server、client session 与单次 response 三层 resource 边界 |
| **`@asynccontextmanager`** | 把含有一次 `yield` 的 `local_server()` 包装成可用于 `async with` 的对象；`yield` 前启动，`finally` 中 cleanup |
| **response body** | `await response.json()` 真正读取并解析承载 `path` 的业务内容 |
| **time budget** | 每个 `fetch_one()` 用 `asyncio.timeout(1.0)` 限制完整 request 与 body 读取等待 |
| **server cleanup** | `runner.cleanup()` 放在 `finally`，即使任一 request 失败也会停止 site 并释放 server resource |

按时间线读输出：

1. `main()` 进入 `async with local_server()`；这个 async context manager 在 `yield` 前启动临时 server，并由系统选择一个当前可用端口。
2. `local_server()` 把 port 与 server stats 交给 `main()`；`main()` 建立 6 个 URL，再创建容量为 2 的 `TCPConnector`。
3. 进入 `ClientSession` 的 async context manager 后，6 个 `fetch_one()` Task 在同一个 `TaskGroup` 中创建。
4. 前两个 request 取得 connection 并到达 server；其余 request Task 等待 connection pool 出现空位。
5. Server 的 `handler()` 把 `active` 增加到最多 2；计数在 `finally` 中恢复，所以失败或 cancellation 也不会留下错误观测值。
6. Client 先用 `response.raise_for_status()` 检查 HTTP status，再在 `await response.json()` 读取 response body；离开 `session.get()` 的边界后，connection 可以被后面的 request 复用。
7. 六个 Task 全部结束后，代码按原始 URL 顺序读取 Task 结果，所以打印顺序稳定，不等同于实际完成顺序。
8. 离开 `ClientSession` 时 client resource 及其默认拥有的 connector 被关闭；随后退出 `local_server()`，它从 `yield` 后恢复并在 `finally` 中调用 `runner.cleanup()`，最后一行明确证明本地 server 已收尾。

## 本节目标

学完本节，你应该能够：

- 使用 aiohttp 执行真实 HTTP request；
- 把 `ClientSession` 当成有 lifecycle 的 resource；
- 理解 connection pool 怎样限制真实 network concurrency；
- 解释 Task 数量为什么不等于真实 connection 数量；
- 使用 async context manager 管理 network resource；
- 为真实 request 复用前课的 time budget；
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

这里复用 Lesson 03 已经见过的 `async with` 与 async context manager；这次它管理的不是 Task 组，而是真实 network resource。

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

在本例中，`ClientSession(connector=connector)` 默认拥有传入的 connector。因此退出 `ClientSession` 的 `async with` 时，session 会连同 connector 和仍由它管理的 connection 一起关闭。这个 ownership 关系很重要：创建 resource 时就要知道最终由谁关闭它。

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

### 4. GET request、HTTP status 与 response body

课程 practice 会批量 GET 一组本地 URL。

```python
async with asyncio.timeout(1.0):
    async with session.get(url) as response:
        response.raise_for_status()
        data = await response.json()
```

这里：

- `session.get(url)` 发起一个 GET request；
- `response` 表示 server 返回的 HTTP response；
- `response.raise_for_status()` 检查 status，4xx / 5xx 时进入异常路径；
- `await response.json()` 读取 response body，并把 JSON 内容转换成 Python 数据结构。

拿到 response 对象，只说明 server 已经返回 response 信息：它既不保证 HTTP status 成功，也不代表 body 已经完整读入内存。先检查 status，再读取 body；network 数据可能还在到达，所以读取 body 仍然可能需要等待。

外层 `asyncio.timeout(1.0)` 给“等待 response + 读取并解析 body”这一整段 client 操作一个 time budget。超时时，当前 `fetch_one()` 会失败；离开 timeout 边界后，调用者看到的是 `TimeoutError`。如果它发生在本例的 `TaskGroup` 中，group 会取消仍未完成的 sibling Task，再等它们完成清理后把错误交给外层。`session.get()`、`ClientSession` 和最外层 server `finally` 分别负责各自那一层的 resource 收尾。

### 5. 为什么测试使用本地 server

课程测试会在当前机器上启动一个临时 HTTP server。

这样可以自己控制：

- 每个 response 返回什么；
- 每次 request 故意等待多久；
- server 同时看到了多少 active request；
- 测试是否稳定重复。

如果测试依赖外部网站，network 波动、外部地址暂时不可用、rate limit 或第三方程序故障都会让验收变得不可靠。

本例的 server 支架按下面的 lifecycle 工作：

```text
进入 async with local_server()
        ↓
web.Application + route
        ↓
AppRunner.setup()
        ↓
TCPSite(..., port=0).start()
        ↓
runner.addresses 取得系统实际分配的 port
        ↓
yield port, stats → client 测试
        ↓
退出边界 → finally → runner.cleanup()
```

`local_server()` 同时使用 `async def` 和 `yield`，所以它原本是 Lesson 07 学过的 async generator function。`@asynccontextmanager` 要求它只 `yield` 一次，并把这一处分成两边：`yield` 前准备并启动 server，`yield` 的值交给 `as` 后面的变量，退出时从 `yield` 后恢复到 `finally`。这正是 Lesson 00 的 `@contextmanager` 模型在 async resource 上的延伸。

`port=0` 表示不把某个固定端口写死，而是让系统选择当前可用端口。`runner.cleanup()` 放在 `finally` 中，因为 client session 与本地 server 是两个独立 resource：关闭前者不会自动关闭后者。即使 `site.start()` 之后的 client 测试失败，server 的 context manager 仍能收尾自己已经启动的 runner。

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

- **误区：** `session.get()` 没有抛异常，就说明 HTTP request 的业务结果成功。
  **更准确：** Server 可以正常返回 4xx / 5xx response；要检查 status，本例使用 `raise_for_status()`。

- **误区：** HTTP 测试必须访问外部网站。  
  **更准确：** 本地 server 更稳定，也更容易测量 active request。

- **误区：** 设置 connection pool limit 后，request 就不可能无限等待。
  **更准确：** 容量上限控制“同时占用多少 connection”，time budget 控制“一次 request 最多愿意等多久”，两者解决不同问题。

- **误区：** `ClientSession` 关闭后，本例的本地 server 也会自动关闭。
  **更准确：** Client 与 server 是独立 resource；本例还必须在 `finally` 中执行 `runner.cleanup()`。

## 本节规则总结

1. Network 让不同程序交换数据；client 发 request，server 回 response。
2. HTTP 是常见的 request / response 规则；URL 表示访问地址；JSON 是常见数据格式；GET 是常见 request 类型。
3. 收到 response 不等于 HTTP 结果成功；先检查 status，再按预期格式读取 body。
4. Connection 是 client 与 server 之间的数据通道；connection pool 管理有限 connection 容量。
5. `ClientSession` 是需要明确关闭的 resource，一批相关 request 通常复用同一个 Session。
6. Connector 管理底层 connection，`TCPConnector(limit=...)` 表达 connection pool 上限。
7. Async context manager 允许进入和退出 resource 时发生 async 等待。
8. Task 数量不等于真实 connection 数量。
9. 读取 response body 仍可能是 async I/O。
10. Network 测试优先使用本地可控 server，而不是依赖外部网站。
11. Connection pool limit 与 request time budget 是两条不同边界，通常需要同时存在。
12. Client、response 与测试 server 各有自己的 lifecycle，异常路径也必须逐层 cleanup。
13. `@asynccontextmanager` 可以用一次 `yield` 把 async resource 的启动、交出和 cleanup 封装成同一个 `async with` 边界。

## 关键问题

1. network 在本课里是什么意思？
2. client 与 server 分别是什么？
3. HTTP request 与 response 分别是什么？
4. URL、`127.0.0.1` 与 port 分别定位什么？
5. JSON 在 request / response 交换中承担什么角色？
6. GET、route 与 handler 怎样把一次 request 连接到处理函数？
7. HTTP status code 表达什么？为什么拿到 response 对象不等于请求成功？
8. `response.raise_for_status()` 在什么情况下进入失败路径？
9. connection 与 connection pool 分别是什么？TCP 在本课模型里处于哪一层？
10. `ClientSession` 为什么是 resource？
11. 为什么不推荐每个 request 都新建一个 `ClientSession`？
12. connector 与 `TCPConnector` 分别负责什么？
13. `TCPConnector(limit=4)` 的 4 表达什么容量？
14. async context manager 与普通 context manager 的关键差别是什么？
15. 100 个 Task + connection pool limit=4 时，真实 network concurrency 为什么不等于 100？
16. 为什么读取 response body 仍可能需要 `await`？
17. 为什么课程测试使用本地 server？`Application`、`AppRunner` 与 `TCPSite` 分别负责哪一层？
18. Connection pool limit 与每个 request 的 time budget 分别控制什么？
19. 为什么退出 `ClientSession` 后仍要在 `finally` 中调用 `runner.cleanup()`？
20. `local_server()` 的 `yield` 前、`yield` 的值和 `finally` 分别对应 server lifecycle 的哪一段？

## 场景命题

批量 GET 一组本地 URL。

要求：

- 使用 aiohttp；
- 一批 request 复用一个 `ClientSession`；
- `TCPConnector` 的 `limit` 可配置；
- 检查每个 response 的 HTTP status，不能把 4xx / 5xx 当作成功数据；
- 每个 response 读取 JSON body；
- 每个 request 都有明确 time budget；
- 返回结果顺序与输入 URL 顺序一致；
- 测试不依赖外部网站；
- 无论 client request 成功还是失败，本地 server runner 最终都必须 cleanup。

验收时同时比较三个数量：创建的 request Task 数、connection pool limit、server 观察到的 active peak。Task 可以明显多于 limit，但 peak 不能超过 limit；最后一行还要能观察到本地 server 已关闭。

练习重点是 client 的 resource 使用方式，不是默写 aiohttp server API。可以从 `case.py` 复制未经修改的 `local_server()` 作为测试支架，再独立实现 `fetch_one()` 与 client 侧 `main()`；完成后再回看支架怎样启动和 cleanup。

---

完成本课后：继续 [Lesson 09 — 让阻塞式普通函数不拖住其他工作](../09_blocking_io/09_blocking_io.md)。
