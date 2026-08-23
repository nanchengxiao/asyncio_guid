# Lesson 03 — 让一组工作在同一个边界内开始和结束

## 进入本课前

你已经学过 Event Loop、Task、`create_task()`、scheduling 和 concurrency。

## 本课新增术语

- **lifecycle（生命周期）**：一份工作从创建、运行到最终结束的完整时间范围。
- **owner（负责人）**：负责创建、等待，并处理某个 Task 最终结果的那一层代码。
- **ownership（负责关系）**：明确“哪个 owner 对哪个 Task 的 lifecycle 负责”的关系。
- **child Task（子任务）**：由当前这层代码创建并负责的 Task。
- **sibling Task（兄弟任务）**：同一个 owner 管理、彼此处在同一层级的 child Task。
- **`TaskGroup`**：Python 3.11 提供的一种管理一组 child Task 的工具；离开它的代码块前，这组 Task 必须已经结束。
- **structured concurrency（结构化并发）**：把一组 child Task 放进一个明确的代码边界，由同一个 owner 统一等待和处理它们的结束。
- **orphan Task（失去负责人任务）**：已经没有清楚 owner，却仍然继续运行的 Task。
- **converge（收敛）**：一组 Task 最终都进入已结束状态，不再留下仍在运行的工作。
- **worker（工作任务）**：负责执行某一类具体业务工作的 child Task。

## 一个例子串起全部术语

上面每个术语单独看都不难，但容易各记各的。下面用一个“点外卖订单”的例子把全部术语串起来：三个 worker 并发推进，其中一个失败。

```python
import asyncio

async def worker(name, delay):
    """worker：只负责一件具体业务的小任务。"""
    try:
        print(f"[{name}] 开工")
        await asyncio.sleep(delay)
        if name == "payment":            # 故意让 payment 这个 worker 失败
            raise RuntimeError("余额不足")
        print(f"[{name}] 完成")
    finally:
        print(f"[{name}] cleanup：收尾自己的资源")

async def handle_order():
    # owner = handle_order 这层代码；lifecycle = async with 块的开始到结束
    async with asyncio.TaskGroup() as tg:       # structured concurrency 的边界
        # 三个 child Task，彼此是 sibling（同一个 owner、同一层级）
        inventory = tg.create_task(worker("inventory", 0.2))
        payment   = tg.create_task(worker("payment", 0.3))    # 会失败
        delivery  = tg.create_task(worker("delivery", 0.4))
    # 执行到这一行之前，整组必须已经 converge
    print("订单处理结束")   # 本例中这一行不会执行

async def main():
    try:
        await handle_order()
    except ExceptionGroup as eg:               # TaskGroup 用异常组向外报告失败
        print(f"调用者收到失败：{eg.exceptions[0]}")

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

把每个术语对到代码上：

| 术语                             | 在这个例子里指什么                                                               |
| -------------------------------- | -------------------------------------------------------------------------------- |
| **lifecycle**              | `async with` 块从进入到退出的时间范围：三个 worker 从创建到全部结束            |
| **owner**                  | `handle_order` 这层代码：创建、等待、处理失败都由它负责                        |
| **ownership**              | “三个 Task 属于`handle_order` 的 `async with` 块”，关系直接写在代码结构里  |
| **child Task**             | `inventory` / `payment` / `delivery` 三个 `tg.create_task(...)` 的返回值 |
| **sibling Task**           | 三个 worker 之间互称：同一个 owner、同一层级                                     |
| **`TaskGroup`**          | 那个`async with` 边界本身                                                      |
| **structured concurrency** | 整组放进明确代码边界，由同一个 owner 统一等待和处理结束                          |
| **worker**                 | 每个只干一件具体事的小任务（查库存 / 扣款 / 配送）                               |
| **converge**               | 一个失败后其余被请求停止、收尾，直到三个都进入结束状态                           |

表里刻意没有 **orphan Task**：它正是这个结构要避免的结果，见下方反例。

按时间线读输出：

1. 三行“开工”：三个 **child Task** 并发推进。
2. `inventory` 完成，`finally` 里执行自己的 **cleanup**（自己的资源自己收尾）。
3. `payment` 抛异常：`TaskGroup` 立刻向还在运行的 sibling（`delivery`）发出**停止请求**。
4. `delivery` 被请求停止：执行自己的 `finally` cleanup 后结束。
5. 整组 **converge**：三个都结束，失败在 `async with` 边界处**向外报告**。
6. 所以“订单处理结束”不会打印：失败沿边界向上传，边界之后的代码不再执行；只有当整组都成功结束时，它才会执行。
7. `main` 收到失败。注意这里抛的是 **`ExceptionGroup`**（异常组）而不是裸的 `RuntimeError`，所以 `except RuntimeError` 接不住，要用 `except ExceptionGroup` 或 `except*`。

如果不用 `TaskGroup`，同样的工作就会退化成 orphan Task：没有 owner 等待它、失败后异常无处可去。这个反例放在下方“为什么不能让 child Task 变成 orphan”。

## 本节目标

学完本节，你应该能够：

- 为每个 Task 指定 owner；
- 解释 ownership 与 lifecycle 边界；
- 解释 structured concurrency 的作用；
- 使用 `TaskGroup` 管理一组 sibling Task；
- 解释一个 child Task 失败后整组 Task 怎样 converge；
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
    inventory = tg.create_task(worker("inventory", 0.2))
    payment   = tg.create_task(worker("payment", 0.3))    # 会失败
    delivery  = tg.create_task(worker("delivery", 0.4))
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

### 4. 为什么不能让 child Task 变成 orphan

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
- **误区：** 所有后台工作都应该放进短 lifecycle `TaskGroup`。
  **更准确：** 真正长期工作的 lifecycle 更长，但仍然必须有明确 owner。

## 本节规则总结

1. Lifecycle 描述一份工作从创建到结束的完整范围。
2. 每个 Task 都应该有清楚 owner 和 ownership。
3. Child Task 的 lifecycle 不应无缘无故超过 owner。
4. `TaskGroup` 把一组 child Task 放进明确共同边界。
5. 一个 sibling 失败后，整组 Task 要先 converge，再离开边界。
6. 不要把“没人负责、但还在运行”的 orphan Task 当作正常设计。
7. 每个 child Task 仍然负责自己的 resource cleanup。

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

## 场景命题

一个父业务操作拥有三个 worker。三个 worker 同时开始，其中一个会失败。

父操作必须：

- 明确拥有这三个 worker；
- 等待整组 converge；
- 让其余尚未结束的 sibling 停止；
- 保证每个 worker 自己的 cleanup 执行；
- 把失败向调用者报告；
- 返回后不遗留本场景创建的 orphan Task。

## 验收

测试会观察：

- sibling 是否收到停止请求；
- cleanup 是否执行；
- 失败是否向外报告；
- 函数返回后是否仍残留本场景创建的 Task。

仓库参考实现：

```bash
uv run pytest lessons/03_structured_concurrency/tests -v
```

完成 starter 后：

```bash
uv run pytest lessons/03_structured_concurrency/tests -v --learner
```
