# Lesson 03 — 让一组工作在同一个边界内开始和结束

## 进入本课前

你已经学过 Event Loop、Task、`create_task()`、scheduling 和 concurrency。

## 本课新增术语

先按三层阅读：谁负责哪些 Task、代码用什么边界表达这种负责关系、整组最终怎样结束。现在只需建立关系，紧接着会全部落到一个失败场景里。

**第一组：Task 之间的负责关系**

- **lifecycle（生命周期）**：一份工作从创建、运行到最终结束的完整时间范围。
- **owner（负责人）**：负责创建、等待，并处理某个 Task 最终结果的那一层代码。
- **ownership（负责关系）**：明确“哪个 owner 对哪个 Task 的 lifecycle 负责”的关系。
- **child Task（子任务）**：由当前这层代码创建并负责的 Task。
- **sibling Task（兄弟任务）**：同一个 owner 管理、彼此处在同一层级的 child Task。

**第二组：把负责关系写成代码边界**

- **`TaskGroup`**：Python 3.11 提供的一种管理一组 child Task 的工具；离开它的代码块前，这组 Task 必须已经结束。
- **`async with`**：与 Lesson 00 的 `with` 一样建立明确代码范围，但进入或退出时允许等待 async 工作；本课退出 `TaskGroup` 时需要等待整组 child Task 结束。
- **async context manager（异步上下文管理器）**：可以放在 `async with` 后面的对象；它负责异步进入和退出这段范围，`TaskGroup` 就是一个例子。
- **structured concurrency（结构化并发）**：把一组 child Task 放进一个明确的代码边界，由同一个 owner 统一等待和处理它们的结束。

**第三组：运行角色与结束结果**

- **orphan Task（失去负责人任务）**：已经没有清楚 owner，却仍然继续运行的 Task。
- **converge（收敛）**：一组 Task 最终都进入已结束状态，不再留下仍在运行的工作。
- **worker（工作任务）**：负责执行某一类具体业务工作的 child Task。
- **`RuntimeError`**：Python 内置的一种普通异常类型；本例只用它表示“payment 检查无法完成”，后续业务课会再使用含义更精确的异常类型。
- **`raise`**：主动抛出一个异常，让当前工作沿失败路径离开；本例用它显式制造 payment 检查失败。
- **`ExceptionGroup`（异常组）**：把一个或多个 child Task 的失败一起带出 `TaskGroup` 边界的异常对象。

## 一个例子串起全部术语

上面每个术语单独看都不难，但容易各记各的。下面用一个“点外卖订单”的例子把全部术语串起来：库存、支付资格和配送范围是三个彼此独立、又都必须通过的下单前检查，因此可以并发推进；其中支付检查被显式设置为失败。代码就是本课的 `case.py`。

```python
import asyncio

async def worker(name, delay, should_fail=False):
    """worker：只负责一件具体业务的小任务。"""
    try:
        print(f"[{name}] 开工")
        await asyncio.sleep(delay)
        if should_fail:                   # 测试行为由参数显式指定，不靠名称猜测
            raise RuntimeError("余额不足")
        print(f"[{name}] 完成")
    finally:
        print(f"[{name}] cleanup：收尾自己的资源")

async def handle_order():
    # owner = handle_order 这层代码；lifecycle = async with 块的开始到结束
    async with asyncio.TaskGroup() as tg:       # structured concurrency 的边界
        # 三个 child Task，彼此是 sibling（同一个 owner、同一层级）
        tg.create_task(worker("inventory", 0.2))
        tg.create_task(worker("payment", 0.3, should_fail=True))
        tg.create_task(worker("delivery", 0.4))
    # 执行到这一行之前，整组必须已经 converge
    print("订单处理结束")   # 本例中这一行不会执行

async def main():
    try:
        await handle_order()
    except ExceptionGroup as group:            # TaskGroup 用异常组向外报告失败
        print(f"调用者收到失败：{group.exceptions[0]}")

asyncio.run(main())
```

真实输出：

```text
[inventory] 开工
[payment] 开工
[delivery] 开工
[inventory] 完成
[inventory] cleanup：收尾自己的资源
[payment] cleanup：收尾自己的资源
[delivery] cleanup：收尾自己的资源
调用者收到失败：余额不足
```

（具体交错顺序可能随调度略有不同，但结构不变。）

把本课知识点对到代码上：

| 术语                             | 在这个例子里指什么                                                               |
| -------------------------------- | -------------------------------------------------------------------------------- |
| **lifecycle**              | `async with` 块从进入到退出的时间范围：三个 worker 从创建到全部结束            |
| **owner**                  | `handle_order` 这层代码：创建、等待、处理失败都由它负责                        |
| **ownership**              | “三个 Task 属于`handle_order` 的 `async with` 块”，关系直接写在代码结构里  |
| **child Task**             | 三次 `tg.create_task(...)` 创建的 inventory / payment / delivery 工作 |
| **sibling Task**           | 三个 worker 之间互称：同一个 owner、同一层级                                     |
| **`TaskGroup`**          | 那个`async with` 边界本身                                                      |
| **`async with` / async context manager** | `asyncio.TaskGroup()` 是 async context manager；进入后创建 child，退出动作可以等待整组结束 |
| **structured concurrency** | 整组放进明确代码边界，由同一个 owner 统一等待和处理结束                          |
| **worker**                 | 每个只做一项下单前检查（库存 / 支付资格 / 配送范围）的小任务                    |
| **`RuntimeError`**         | `RuntimeError("余额不足")` 是本例交给 `raise` 的普通失败对象                  |
| **`raise`**                | `raise RuntimeError("余额不足")` 让 payment 沿明确失败路径离开，而不是靠名称或随机条件暗中失败 |
| **converge**               | 一个失败后其余被请求停止、收尾，直到三个都进入结束状态                           |
| **`ExceptionGroup`**       | 整组 converge 后，`TaskGroup` 用它把 `payment` 的失败带给 `main()`               |

表里刻意没有 **orphan Task**：它正是这个结构要避免的结果，见下方反例。

按时间线读输出：

1. 三行“开工”：三个 **child Task** 并发推进。
2. `inventory` 完成，`finally` 里执行自己的 **cleanup**（自己的资源自己收尾）。
3. `payment` 抛异常：`TaskGroup` 立刻向还在运行的 sibling（`delivery`）发出**停止请求**。
4. `delivery` 被请求停止：执行自己的 `finally` cleanup 后结束。
5. 整组 **converge**：三个都结束，失败在 `async with` 边界处**向外报告**。
6. 所以“订单处理结束”不会打印：失败沿边界向上传，边界之后的代码不再执行；只有当整组都成功结束时，它才会执行。
7. `main` 收到失败。注意这里抛的是 **`ExceptionGroup`** 而不是裸的 `RuntimeError`，所以本例在边界外使用 `except ExceptionGroup`。

如果不用 `TaskGroup`，同样的工作就会退化成 orphan Task：没有 owner 等待它、失败后异常无处可去。这个反例放在下方“为什么不能让 child Task 变成 orphan”。

## 本节目标

学完本节，你应该能够：

- 为每个 Task 指定 owner；
- 解释 ownership 与 lifecycle 边界；
- 解释 structured concurrency 的作用；
- 使用 `TaskGroup` 管理一组 sibling Task；
- 解释一个 child Task 失败后整组 Task 怎样 converge；
- 解释为什么 `TaskGroup` 用 `ExceptionGroup` 向边界外报告 child 失败；
- 识别 orphan Task 风险。

## 为什么需要学习它

到处散落的 `create_task()` 最大问题通常不是语法，而是责任不清：

- 谁等待它？
- 父业务已经结束时，它还能不能继续？
- 它失败后谁看见异常？
- 其他同组工作还要不要继续？

Structured concurrency 的价值，就是把 ownership 写进代码结构本身。

## 核心理论

### 1. `TaskGroup` 把一组 Task 放进明确边界

上面例子里的 `handle_order` 就是这个结构：三个 worker 放进同一个边界。

```python
async with asyncio.TaskGroup() as tg:
    tg.create_task(worker("inventory", 0.2))
    tg.create_task(worker("payment", 0.3, should_fail=True))
    tg.create_task(worker("delivery", 0.4))
```

把整个边界理解成一个闭环：

```text
进入 TaskGroup
   ↓
owner 创建 child Task
   ↓
child Task concurrency 推进
   ↓
离开 TaskGroup 前
   ↓
所有 child Task 都已经结束
```

父代码不会在自己创建的 child Task 还悬着时直接越过这个 lifecycle 边界。

### 2. Owner 不只是“谁调用了 create_task”

一个清楚的 owner 至少负责回答：

1. 谁创建这个 Task？
2. 谁等待它结束？
3. 它失败后谁处理结果？
4. 父业务不再需要它时，谁负责让它停下来？

对照上面的例子：`handle_order`（连同它里面的 `TaskGroup`）把这四个问题都写进了结构——创建三个 worker、等整组 converge、把失败报告给 `main`、在 sibling 失败时请求其余停止。

如果这些问题只能靠“以后应该有人处理”来回答，ownership 就不清楚。

### 3. 一个 sibling 失败时，整组需要 converge

假设同一个 `TaskGroup` 里有三个 sibling Task，其中一个因普通异常失败。

`TaskGroup` 会请求其他尚未完成的 sibling 停止，然后等待整组 Task 都进入结束状态，再把失败向外报告。这正是上面时间线第 3–5 步：`payment` 失败 → `delivery` 被请求停止 → 整组 converge。

这里先只记住“请求停止”这个行为。下一课会正式解释 Python 用什么机制表达这种停止请求。

### 4. 边界外收到的是 `ExceptionGroup`

`TaskGroup` 允许多份 child Task 并发运行，因此退出边界时可能需要同时报告不止一个失败。它统一使用 `ExceptionGroup` 保存这些异常：

```python
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(worker())
except ExceptionGroup as group:
    print(group.exceptions)
```

即使本例最后只有 `payment` 的一个 `RuntimeError`，它仍然装在 `ExceptionGroup` 中。因此边界外不能直接用 `except RuntimeError` 接住它。

本课只先建立“整组失败一起越过边界”的模型。后面会继续学习怎样按异常类型处理组内的多个失败。

### 5. 为什么不能让 child Task 变成 orphan

把好例子的 `handle_order` 改成下面这样：

```python
async def handle_order():                        # 反例：不用 TaskGroup
    asyncio.create_task(worker("delivery", 0.4))   # 没有 owner 等待它
    return {"ok": True}
```

`handle_order` 已经返回，但 `delivery` 仍在运行，这时就要问：

- 谁等待它？
- 程序退出时谁负责它？
- 它失败后异常去哪？

对比好例子：同一个 `delivery` worker，放进 `TaskGroup` 里就有人负责；直接 `create_task` 后丢下它返回，它就退化成 orphan Task。

有些真正长期存在的后台工作可以有更长 lifecycle 和更长 lifecycle 的 owner，但这个 owner 必须明确，而不是默认“丢到后台就行”。

## 脑内执行模型

```text
owner（handle_order）
  │
  └─ TaskGroup
      ├─ inventory ──── 完成 → cleanup → 结束
      ├─ payment ────── 失败 → cleanup → 结束
      └─ delivery ───── 停止请求 → cleanup → 结束

owner 等整组 converge 后才离开 TaskGroup
```

这里的 `cleanup` 已经在 Lesson 00 定义过：child Task 自己使用的 resource，仍然要由它自己的代码可靠收尾。失败的 `payment` 也一样——异常离开它之前，它自己的 `finally` 仍然会执行。

## 常见误解

- **误区：** `TaskGroup` 只是“更短的批量等待语法”。**更准确：** 它还明确了 child Task 的 owner 和共同 lifecycle 边界。
- **误区：** Task 最后某处能被 `await` 就说明 ownership 清楚。**更准确：** owner 应该在代码结构上可以直接定位。
- **误区：** sibling 被请求停止一定是额外错误。**更准确：** 如果它们共同组成一次业务工作，关键 child 失败后停止其余工作通常更符合业务边界。
- **误区：** `TaskGroup` 会把异常吃掉。**更准确：** 它先等整组 converge，再把失败向外报告。
- **误区：** Child 抛出 `RuntimeError`，边界外一定能直接 `except RuntimeError`。**更准确：** `TaskGroup` 用 `ExceptionGroup` 统一报告 child 失败。
- **误区：** 所有后台工作都应该放进短 lifecycle `TaskGroup`。
  **更准确：** 真正长期工作的 lifecycle 更长，但仍然必须有明确 owner。

## 本节规则总结

1. Lifecycle 描述一份工作从创建到结束的完整范围。
2. 每个 Task 都应该有清楚 owner 和 ownership。
3. Child Task 的 lifecycle 不应无缘无故超过 owner。
4. `TaskGroup` 把一组 child Task 放进明确共同边界。
5. `async with` 允许 async context manager 在退出边界时等待异步收尾；`TaskGroup` 用它等待 child。
6. 一个 sibling 失败后，整组 Task 要先 converge，再离开边界。
7. 不要把“没人负责、但还在运行”的 orphan Task 当作正常设计。
8. 每个 child Task 仍然负责自己的 resource cleanup。
9. `TaskGroup` 用 `ExceptionGroup` 把一个或多个 child 失败带到边界外。
10. 测试失败场景要显式传入条件，并用 `raise` 进入失败路径，不要让名称暗中决定行为。

## 关键问题

1. lifecycle 在本课里是什么意思？
2. owner 与 ownership 有什么区别？
3. owner 最少要回答哪几个 lifecycle 问题？
4. child Task 和 sibling Task 分别是什么意思？
5. structured concurrency 解决的核心问题是什么？
6. `TaskGroup` 为什么能让 ownership 更清楚？
7. 一个 sibling 失败后，其余 sibling 会怎样？
8. converge 在本课里具体表示什么？
9. orphan Task 有什么风险？
10. 哪类长期工作可能不适合放进一次短 lifecycle `TaskGroup`？
11. 为什么本例不能直接用 `except RuntimeError` 捕获 `payment` 的失败？
12. `async with` 相比普通 `with` 多允许了什么？为什么 `TaskGroup` 适合使用这个边界？
13. 本例为什么把 `should_fail=True` 明确写在 payment worker 的创建位置？

## 场景命题

一个父业务操作拥有三个 worker。三个 worker 同时开始，其中一个会失败。

父操作必须：

- 明确拥有这三个 worker；
- 等待整组 converge；
- 让其余尚未结束的 sibling 停止；
- 保证每个 worker 自己的 cleanup 执行；
- 把失败向调用者报告；
- 返回后不遗留本场景创建的 orphan Task。

验收时至少观察：三个 worker 都开始；失败发生后每个 worker 都执行 cleanup；父操作只在整组 converge 后收到 `ExceptionGroup`；边界后的成功日志不会错误打印。

---

完成本课后：继续 [Lesson 04 — 正确响应“停止这份工作”](../04_cancellation/04_cancellation.md)。
