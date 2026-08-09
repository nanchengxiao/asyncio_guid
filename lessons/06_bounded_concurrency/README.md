# Lesson 06 — 限制同时占用稀缺资源的工作数量

## 进入本课前

你已经学过 Task、concurrency、TaskGroup、timeout 和 cancellation。

## 本课新增术语

- **job（作业）**：系统要处理的一条独立工作，例如“抓取一个 URL”或“处理一条订单”。
- **bounded concurrency（有上限的并发）**：允许多份工作同时进行，但同时进行的数量不能超过明确上限。
- **Semaphore（信号量）**：可以把它理解成有限数量的“通行证”；没有通行证的 Task 要等待。
- **downstream（下游）**：当前代码接下来要调用、并且可能有容量限制的外部服务或资源。
- **active concurrency（正在占用资源的并发量）**：此刻真正进入受保护区域、正在使用稀缺资源的工作数量。
- **backlog（积压）**：已经进入系统，但还没有轮到真正处理的工作。
- **peak（峰值）**：一段观察时间里，某个数量曾经达到过的最大值。
- **rate limit（速率限制）**：限制单位时间内最多允许启动多少次调用，而不是限制同一时刻有多少调用正在进行。

## 本节目标

学完本节，你应该能够：

- 解释为什么 Task 数量不等于资源容量；
- 用 `Semaphore` 表达 active concurrency 上限；
- 区分 active concurrency 与 backlog；
- 区分 concurrency limit 与 rate limit；
- 测量真实 peak active concurrency。

## 为什么需要学习它

输入数量可以远远大于 downstream 真正能同时承受的调用数量。

例如系统有 10 万条 job，但某个 downstream 同一时间只允许 20 个调用。把 10 万个 Task 全部同时推进到这个资源，并不会让处理更快，只会制造更多等待、内存占用和 timeout。

真正需要控制的是：

> 同一时刻到底有多少份工作正在占用这项稀缺资源？

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

### 2. 通行证只应该包围真正稀缺的资源区

不要写成：

```python
async with sem:
    prepare_input()
    validate_input()
    result = await call_downstream()
```

如果准备和校验根本不消耗那项稀缺资源，就没有必要让它们占着通行证。

更合理的是：

```python
prepare_input()
validate_input()

async with sem:
    result = await call_downstream()
```

原则是：

> Semaphore 保护“真正占用有限资源”的最小必要范围。

### 3. Active concurrency 与 backlog 是两个不同数量

假设一次性创建 10 万个 Task，但 `Semaphore(10)` 只允许 10 个进入资源区。

那么：

```text
active concurrency = 最多 10
backlog            = 仍可能有大量 Task 在等待
```

所以 Semaphore 可以限制 active concurrency，却不会自动让整个系统“所有数量都有限”。

下一课会继续解决：等待中的工作也很多时，怎样给 backlog 建立边界。

### 4. Concurrency limit 与 rate limit 控制不同维度

可以用两个问题区分：

```text
concurrency limit → 这一时刻最多有多少个调用正在进行？
rate limit        → 这一秒最多允许启动多少个新调用？
```

例如一个调用平均持续 10 秒：

- concurrency limit=10，可能一直保持 10 个调用在途；
- rate limit=2/s，表示每秒最多新启动 2 个调用。

两者不是一回事。

本课只要求你先能区分；最后一课会把两种限制放进同一个长期运行服务。

### 5. 测试要观察真实 peak

如果想验证并发上限，不能只看代码里有没有 `Semaphore`。

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
J1 ─ prepare ─ [resource] ─ finish
J2 ─ prepare ─ [resource] ─ finish
J3 ─ prepare ─ wait permit ─ [resource]
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

- **误区：** 创建很多 Task 再加 `Semaphore`，系统就完全有界。  
  **更准确：** active concurrency 有界，但 backlog 仍可能很大。

- **误区：** concurrency limit 就是“每秒请求数”。  
  **更准确：** 前者控制同一时刻正在进行多少调用；rate limit 控制单位时间启动多少调用。

- **误区：** Semaphore 应该包住整个 worker。  
  **更准确：** 它应该尽量只包围真正消耗稀缺资源的部分。

- **误区：** 测试只要搜索到 `Semaphore` 就能证明行为正确。  
  **更准确：** 应观察真实 peak。

## 本节规则总结

1. 先识别真正稀缺的 downstream 资源。
2. `Semaphore` 用有限通行证限制 active concurrency。
3. 通行证只覆盖真正占用资源的必要范围。
4. Bounded concurrency 不等于 bounded backlog。
5. Concurrency limit 与 rate limit 控制不同维度。
6. Peak 表示观察期间出现过的最大数量。
7. 验收并发上限时，应观察真实 active peak。

## 关键问题

1. job 在本课里是什么意思？
2. `Semaphore(10)` 的 10 表示什么？
3. downstream 是什么意思？
4. active concurrency 与 backlog 有什么区别？
5. peak 在测试里表达什么？
6. 为什么 `Semaphore` 应尽量只包住真正稀缺的资源区？
7. 为什么 bounded concurrency 仍可能有巨大 backlog？
8. concurrency limit 和 rate limit 分别控制什么？
9. 为什么行为测试比搜索某个工具名更可靠？

## 场景命题

批量调用一个容量有限的 downstream。

输入可以很多，但同一时间进入 `fetch_one` 的调用不能超过 `limit`；当 `limit > 1` 时，也不能退化成完全按顺序一个一个执行。

## 验收

测试会记录 active / peak 计数，并确认：

- 所有结果正确；
- peak 不超过 `limit`；
- `limit > 1` 时确实保留 concurrency；
- 限制发生在真正的 downstream 调用区域。

仓库参考实现：

```bash
uv run pytest lessons/06_bounded_concurrency/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/06_bounded_concurrency/tests -v --learner
```
