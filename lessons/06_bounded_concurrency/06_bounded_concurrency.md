# Lesson 06 — 限制同时占用稀缺 resource 的工作数量

## 进入本课前

你已经学过 Task、concurrency、TaskGroup、timeout 和 cancellation。

## 本课新增术语

- **job（作业）**：系统要处理的一条独立工作，例如“处理一条订单”。
- **bounded concurrency（有上限的并发）**：允许多份工作同时进行，但同时进行的数量不能超过明确上限。
- **active concurrency（正在占用资源的并发量）**：此刻真正进入受保护区域、正在使用稀缺 resource 的工作数量。
- **concurrency limit（并发上限）**：允许 active concurrency 达到的最大数量。
- **Semaphore（信号量）**：可以把它理解成有限数量的“通行证”；没有通行证的 Task 要等待。
- **downstream（下游）**：当前代码接下来要调用、并且可能有容量限制的外部系统或 resource。
- **backlog（积压）**：已经进入程序，但还没有轮到真正处理的工作。
- **peak（峰值）**：一段观察时间里，某个数量曾经达到过的最大值。
- **rate limit（速率限制）**：限制单位时间内最多允许启动多少次调用，而不是限制同一时刻有多少调用正在进行。
- **`task.result()`**：读取一个已经结束的 Task 的返回值；如果 Task 尚未结束或已经失败，就不能把它当作正常结果读取。

## 一个例子串起全部术语

下面一次创建 10 个 job，但 downstream 同一时刻只允许 3 份工作真正进入。除了限制数量，代码还主动记录真实 active concurrency 的 peak，证明限制确实生效。代码就是本课的 `case.py`：

```python
import asyncio

LIMIT = 3                          # concurrency limit

async def call_downstream(item, stats):
    stats["active"] += 1           # 记录真实行为，而不是搜索源码里的工具名
    stats["peak"] = max(stats["peak"], stats["active"])
    try:
        await asyncio.sleep(0.1)   # 真正占用稀缺 downstream resource 的调用
        return item * 10
    finally:
        # 即使失败或 cancellation，也不能让观测值永远多算一份 active 工作
        stats["active"] -= 1

async def process(item, semaphore, stats):
    # 准备、校验不占通行证；通行证只包围真正消耗 resource 的最小范围
    async with semaphore:
        return await call_downstream(item, stats)

async def main():
    semaphore = asyncio.Semaphore(LIMIT)  # 由本次 operation 创建并拥有
    stats = {"active": 0, "peak": 0}
    tasks = []
    async with asyncio.TaskGroup() as tg:
        for item in range(10):
            tasks.append(tg.create_task(process(item, semaphore, stats)))
    print([task.result() for task in tasks])
    print(f"active concurrency 峰值 peak = {stats['peak']}（limit = {LIMIT}）")
    # Semaphore 限制的是 active concurrency；等待中的 backlog 是另一个数量

asyncio.run(main())
```

真实输出：

```text
[0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
active concurrency 峰值 peak = 3（limit = 3）
```

把本课知识点对到代码上：

| 术语或知识点 | 在这个例子里指什么 |
| --- | --- |
| **job** | `range(10)` 中每个 `item` 对应一条独立处理工作 |
| **bounded concurrency** | 10 份 Task 都可以存在，但同一时刻最多 3 份进入 `call_downstream()` |
| **active concurrency** | `stats["active"]` 记录此刻已经取得通行证、正在调用 downstream 的工作数 |
| **concurrency limit** | `LIMIT = 3` 是 active concurrency 允许达到的上限 |
| **Semaphore** | `main()` 创建的 `semaphore` 提供 3 张通行证；`async with semaphore` 自动取得并归还 |
| **downstream** | `call_downstream()` 模拟当前程序要调用的有限外部 resource |
| **backlog** | 已创建但还在 `async with semaphore` 前等待通行证的 Task；它没有被 Semaphore 消除 |
| **peak** | `stats["peak"]` 保存运行期间实际观察到的 active 最大值 |
| **ownership 与 cleanup** | Semaphore 和观测状态由本次 `main()` 创建；`finally` 保证失败或 cancellation 时也把 active 计数减回去 |
| **rate limit** | 本例没有实现 rate limit；它只限制“同时有几个”，没有限制“每秒新启动几个” |
| **`task.result()`** | 只在 `TaskGroup` 已正常退出后读取每个 Task 的结果，因此这些 Task 已经结束且没有失败 |

按时间线读输出：

1. `TaskGroup` 很快创建 10 个 `process()` Task，所以 Task 总数大于 resource 容量。
2. 前 3 个 Task 分别取得一张 Semaphore 通行证，进入 `call_downstream()`。
3. `stats["active"]` 依次升到 3，`stats["peak"]` 也更新为 3；其余 Task 在通行证外形成 backlog。
4. 其中一个 downstream 调用结束后离开 `async with sem`，自动归还一张通行证。
5. 一个等待中的 Task 随后取得通行证进入；这个过程分批重复，但 `active` 从未超过 3。
6. 10 个 Task 全部结束后，`TaskGroup` 才退出；结果仍按创建时保存的 Task 顺序读取。
7. 最后一行打印 `peak = 3`，用真实运行行为证明 concurrency limit 生效，而不只是证明代码里写了 Semaphore。

## 本节目标

学完本节，你应该能够：

- 解释为什么 Task 数量不等于 resource 容量；
- 用 `Semaphore` 表达 concurrency limit；
- 区分 active concurrency 与 backlog；
- 区分 concurrency limit 与 rate limit；
- 测量真实 peak active concurrency。

## 为什么需要学习它

输入数量可以远远大于 downstream 真正能同时承受的调用数量。

例如系统有 10 万条 job，但某个 downstream 同一时间只允许 20 个调用。把 10 万个 Task 全部同时推进到这个 resource，并不会让处理更快，只会制造更多等待、内存占用和 timeout。

真正需要控制的是：

> 同一时刻到底有多少份工作正在占用这项稀缺 resource？

## 核心理论

### 1. `Semaphore` 像有限数量的通行证

```python
sem = asyncio.Semaphore(10)

async with sem:
    result = await fetch_one(item)
```

`Semaphore(10)` 可以先理解成只有 10 张通行证。

```text
很多 Task
   ↓
Semaphore(10)
   ↓
最多 10 个同时进入受保护区域
```

第 11 个 Task 不会因为没有通行证而立即失败；它会等待，直到前面的 Task 释放一张通行证。

### 2. 通行证只应该包围真正稀缺的 resource 区域

不要写成：

```python
async with sem:
    prepare_input()
    validate_input()
    result = await call_downstream()
```

如果准备和校验根本不消耗那项稀缺 resource，就没有必要让它们占着通行证。

更合理的是：

```python
prepare_input()
validate_input()

async with sem:
    result = await call_downstream()
```

原则是：

> Semaphore 保护“真正占用有限 resource”的最小必要范围。

`async with semaphore` 还会在正常返回、普通异常和 cancellation 路径上归还通行证。与 resource 占用同步变化的观测计数也应放在 `try/finally` 中恢复，否则一次中途失败就可能让 `active` 永久多算。

### 3. Active concurrency 与 backlog 是两个不同数量

假设一次性创建 10 万个 Task，但 `Semaphore(10)` 只允许 10 个进入 resource 区域。

那么：

```text
active concurrency = 最多 10
backlog            = 仍可能有大量 Task 在等待
```

所以 Semaphore 可以限制 active concurrency，却不会自动让整个程序“所有数量都有限”。

下一课会继续解决：等待中的工作也很多时，怎样给 backlog 建立边界。

### 4. Concurrency limit 与 rate limit 控制不同维度

可以用两个问题区分：

```text
concurrency limit → 这一时刻最多有多少个调用正在进行？
rate limit        → 这一秒最多允许启动多少个新调用？
```

例如一个调用平均持续 10 秒：

- concurrency limit=10，可能一直保持 10 个调用正在进行；
- rate limit=2/s，表示每秒最多新启动 2 个调用。

两者不是一回事。

本课只要求你先能区分；最后一课会把两种限制放进同一个长期运行程序。

### 5. 测试要观察真实 peak

如果想验证 concurrency limit，不能只看代码里有没有 `Semaphore`。

更可靠的行为测试是记录：

```text
active += 1
peak = max(peak, active)
...
active -= 1
```

然后断言：

```text
peak <= limit
```

这样测试的是实际行为，而不是某个工具名是否出现在源码里。

## 脑内执行模型

```text
J1 ─ 准备 ─ [占用 resource] ─ 完成
J2 ─ 准备 ─ [占用 resource] ─ 完成
J3 ─ 准备 ─ 等待通行证 ─ [占用 resource]
                  ↑ active concurrency <= limit
```

当输入很多时：

```text
大量 job
   ├─ 少量正在占用 downstream → active concurrency
   └─ 大量还没轮到           → backlog
```

## 常见误解

- **误区：** `Semaphore` 越小越安全。  
  **更准确：** 太小也会浪费 downstream 本来可以承受的容量。

- **误区：** 创建很多 Task 再加 `Semaphore`，程序就完全有界。  
  **更准确：** active concurrency 有界，但 backlog 仍可能很大。

- **误区：** concurrency limit 就是“每秒请求数”。  
  **更准确：** 前者控制同一时刻正在进行多少调用；rate limit 控制单位时间启动多少调用。

- **误区：** Semaphore 应该包住整个 worker。  
  **更准确：** 它应该尽量只包围真正消耗稀缺 resource 的部分。

- **误区：** 测试只要搜索到 `Semaphore` 就能证明行为正确。  
  **更准确：** 应观察真实 peak。

## 本节规则总结

1. 先识别真正稀缺的 downstream resource。
2. `Semaphore` 用有限通行证限制 active concurrency。
3. Concurrency limit 表示 active concurrency 的最大允许值。
4. 通行证只覆盖真正占用 resource 的必要范围。
5. Bounded concurrency 不等于 bounded backlog。
6. Concurrency limit 与 rate limit 控制不同维度。
7. Peak 表示观察期间出现过的最大数量。
8. 验收 concurrency limit 时，应观察真实 active peak。

## 关键问题

1. job 在本课里是什么意思？
2. active concurrency 与 concurrency limit 有什么区别？
3. `Semaphore(10)` 的 10 表示什么？
4. downstream 是什么意思？
5. active concurrency 与 backlog 有什么区别？
6. peak 在测试里表达什么？
7. 为什么 `Semaphore` 应尽量只包住真正稀缺的 resource 区域？
8. 为什么 bounded concurrency 仍可能有巨大 backlog？
9. concurrency limit 和 rate limit 分别控制什么？
10. 为什么行为测试比搜索某个工具名更可靠？
11. 为什么本例只在 `TaskGroup` 退出后调用 `task.result()`？

## 场景命题

批量调用一个容量有限的 downstream。

输入可以很多，但同一时间进入 `fetch_one` 的调用不能超过 `limit`；当 `limit > 1` 时，也不能退化成完全按顺序一个一个执行。

要求：

- Semaphore 由本次批处理 operation 创建，再明确传给 child Task，不依赖跨运行残留的全局状态；
- 通行证只包围真正调用 downstream 的最小代码范围；
- 用 `active` 和 `peak` 记录真实行为，并在 `finally` 中恢复 `active`；
- 验收 `peak <= limit`，同时在 `limit > 1` 时确认 `peak > 1`；
- 解释为什么这个实现仍然没有限制等待中的 Task 总量。

---

完成本课后：继续 [Lesson 07 — 让等待中的工作也有明确上限](../07_queue_and_backpressure/07_queue_and_backpressure.md)。
