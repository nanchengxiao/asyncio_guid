# Python Asyncio（2）：可等待对象、任务与 Future

> 原文：**Python Asyncio Part 2 – Awaitables, Tasks, and Futures**  
> 来源：https://bbc.github.io/cloudfit-public-docs/asyncio/asyncio-part-2.html  
> 中文翻译整理日期：2026-07-25  
> 说明：代码与 API 名称尽量保持原样；文中的 Python 3.6～3.10 版本说明反映原文写作和后续修订时的状态。

第 1 篇介绍了 `asyncio` 的基本概念。本篇进一步讨论在 Python 代码中使用这个库时的具体语法。许多示例来自 BBC R&D Cloudfit 项目中实际使用过的代码模式。

## 编写异步代码

Python 异步程序员最基础的工具是 `async def`。它声明异步协程函数的方式，与 `def` 声明普通同步函数的方式相似。

> **术语说明**  
> 本系列为了表达方便，会把 `async def`、`async for`、`async with` 当作整体称为“关键字”。严格来说，`async` 和 `def` 才是独立关键字；但由于 `async` 不能单独使用，把它们视为带空格的组合关键字更直观。

```python
async def example_coroutine_function(a, b):
    # 异步代码写在这里
    ...


def example_function(a, b):
    # 同步代码写在这里
    ...
```

这里定义了一个协程函数 `example_coroutine_function` 和一个普通函数 `example_function`。后者的函数体是普通同步 Python，前者的函数体则是异步 Python 代码。

> **重要**
>
> - 异步 Python 代码只能写在允许异步语法的上下文中；几乎总是指由 `async def` 定义的协程函数体。第 3 篇还会介绍另一种允许异步代码出现的上下文。
> - 异步代码仍然可以使用普通 Python 中允许的所有关键字和结构；没有哪种普通语言结构被禁止，尽管有些做法并不推荐。
> - `await`、`async with` 和 `async for` 只能用于异步代码中。
> - `async def` 本身并不局限于异步上下文；凡是能够写 `def` 的位置，通常也能写 `async def`，只是两者创建的对象和调用行为不同。

`async def` 的声明看起来与 `def` 很像，但有几个关键差异。

### `def` 的调用行为

```python
def example_function(a, b, c):
    ...
```

这会创建一个名为 `example_function` 的可调用对象。执行：

```python
r = example_function(1, 2, 3)
```

函数体会立即以子程序调用的方式运行，返回值被赋给 `r`。

### `async def` 的调用行为

```python
async def example_coroutine_function(a, b, c):
    ...
```

这会创建一个名为 `example_coroutine_function` 的可调用对象，但执行：

```python
r = example_coroutine_function(1, 2, 3)
```

**不会立即运行函数体。** 相反，它会创建一个 `Coroutine` 类的对象，并把它赋给 `r`。要让函数体真正执行，需要使用 `asyncio` 提供的协程运行机制，最常见的是 `await`；`asyncio.gather` 也可以调度协程。

> **术语：coroutine 的三种常见指代**
>
> 人们经常不严格地区分“协程”一词所指的对象：
>
> 1. `async def` 语句中的异步代码块；
> 2. `async def` 创建的可调用对象，即**协程函数**；
> 3. 调用协程函数后返回的 `Coroutine` 实例，即**协程对象**。
>
> 本文尽量明确区分：用“协程函数”表示可调用对象，用“协程对象”表示调用后得到的对象。

> **类型提示**
>
> ```python
> async def example_coroutine_function(a: A, b: B) -> C:
>     ...
> ```
>
> 从类型系统角度看，这个函数接收 `A`、`B` 类型的参数，并返回 `Coroutine[Any, Any, C]`。通常无需显式写出这个返回类型。
>
> 两个 `Any` 与事件循环内部的协程驱动协议有关：第一个表示协程让出控制权时传给事件循环的值类型，第二个表示事件循环恢复协程时传回的值类型。客户端代码通常不需要接触它们，除非你在实现自己的事件循环。

## `await` 与可等待对象

`await` 是异步代码的核心。它只能出现在允许异步语法的代码块中，例如 `async def` 的函数体。它是一个接收单个对象并产生一个值的表达式。

```python
r = await a
```

这会对对象 `a` 执行等待操作，并把得到的值赋给 `r`。具体行为取决于 `a` 是什么对象。

### 等待协程对象

协程对象是“可等待的（awaitable）”，因此可用于 `await` 表达式。

异步代码总是在某个 `Task` 的上下文中执行，而每个任务有自己的调用栈。第一次等待某个协程对象时，该协程的代码块会在**当前任务**中执行；新的代码上下文像普通函数调用一样被压入该任务的栈。

当协程代码块执行到末尾或通过 `return` 返回时，执行回到发起等待的 `await` 表达式。表达式的值就是协程返回的值。同一个协程对象若被第二次等待，会抛出异常。

因此，可以把“等待协程对象”理解为近似于“调用函数”，但有一个重要区别：协程函数体可以包含异步代码，所以执行期间可能暂停当前任务；普通函数调用不能以这种方式把控制权交还给事件循环。

### 三类可等待对象

实际上有三类对象可用于 `await`：

1. **协程对象（Coroutine）**：被等待时，在当前任务内执行其代码块；`await` 返回该代码块的返回值。
2. **`asyncio.Future` 实例**：被等待时，可能让当前任务暂停，直到某个条件满足或外部过程完成。
3. **实现了 `__await__` 魔术方法的对象**：其等待行为由该方法定义。

第三种机制允许库作者创建自定义可等待类型。一般应让自定义对象表现得像协程或 Future，并在文档字符串中明确说明。为同步 I/O 库编写 `asyncio` 包装器时，可能会用到这项较高级的技术。

> **类型提示**  
> `typing.Awaitable` 是泛型抽象类型。`Awaitable[R]` 表示“可被等待，并在 `await` 后产生 `R` 类型结果的任意对象”。

### `await` 是任务可能切换的检查点

一个非常重要的原则是：当前任务只有在等待 Future（或行为类似 Future 的自定义可等待对象）时，才可能暂停。这样的暂停只会发生在异步代码中。

因此：

- 任意 `await` 表达式**可能**暂停当前任务，但不保证一定暂停；如果被等待对象已经完成，它可能立即返回。
- 不包含 `await` 的普通语句不能暂停当前任务。第 3 篇会说明 `async for` 和 `async with` 在何种情况下也会形成暂停点。

这使异步程序中的传统数据竞争问题比多线程程序少得多，但并未完全消失。对于同一事件循环中多个任务共享的数据，可以把两个等待点之间的同步代码看作“原子的”：事件循环不会在这段代码中间强制切换任务。

```python
import asyncio


async def get_some_values_from_io():
    # 一段 I/O 代码，返回一个值列表
    ...


vals = []


async def fetcher():
    while True:
        io_vals = await get_some_values_from_io()

        for val in io_vals:
            vals.append(io_vals)


async def monitor():
    while True:
        print(len(vals))
        await asyncio.sleep(1)


async def main():
    t1 = asyncio.create_task(fetcher())
    t2 = asyncio.create_task(monitor())
    await asyncio.gather(t1, t2)


asyncio.run(main())
```

`fetcher` 和 `monitor` 虽然都访问全局变量 `vals`，但它们运行在同一事件循环的不同任务中。`fetcher` 的 `for` 循环体中没有 `await`，所以 `monitor` 不可能在该循环执行到一半时插入运行。

若 `get_some_values_from_io` 每次总返回 10 个值，那么 `monitor` 看到的列表长度总会是 10 的倍数。倘若 `for` 循环内部加入了 `await`，这个保证便不再成立。

> **注意**  
> 上例中的两个 `create_task` 并非必需；`main` 的主体可以简化为：
>
> ```python
> await asyncio.gather(fetcher(), monitor())
> ```

## Future

`Future` 是一种可等待对象。与协程对象不同，等待 Future 不会因此启动某个代码块。可以把 Future 理解为：它代表一个正在别处进行、可能已经完成也可能尚未完成的过程。

等待 Future 时：

- 若代表的过程已完成并返回值，`await` 立即返回该值。
- 若过程已完成并抛出异常，`await` 立即重新抛出该异常。
- 若过程尚未完成，当前任务暂停；过程完成后，再按上面两种情况之一处理。

除可等待之外，所有 Future 对象 `f` 还提供同步接口：

- `f.done()`：过程已结束时返回 `True`。
- `f.exception()`：尚未结束时抛出 `asyncio.InvalidStateError`；已结束时返回过程抛出的异常，若正常结束则返回 `None`。
- `f.result()`：尚未结束时抛出 `asyncio.InvalidStateError`；已结束且失败时重新抛出异常，正常结束时返回结果。

Future 一旦进入“已完成”状态，就不可能回到“未完成”状态；完成是一次性的状态变化。

> **重要：协程与 Future 的区别**  
> 协程对象的代码在被等待或包装成任务之前不会执行。Future 则代表某个已经在别处进行的过程；它让你等待过程完成、检查状态并取得结果。

应用开发者通常不会直接创建 Future，除非在实现扩展 `asyncio` 的底层库。许多库函数会返回 Future。确有需要时可这样创建：

```python
f = asyncio.get_running_loop().create_future()
```

更常用的是与之相关的 `create_task`。

> **类型提示**
>
> ```python
> f: asyncio.Future[R]
> ```
>
> 表示一个完成后产生 `R` 类型结果的 Future。原文指出，在 Python 3.6 中可能需要把 `asyncio.Future[R]` 写成字符串形式；后续版本通常不需要。

## Task

每个事件循环包含多个任务，每个正在执行的协程都运行在某个任务中。因此，如何创建任务非常关键。

```python
async def example_coroutine_function():
    ...


t = asyncio.create_task(example_coroutine_function())
```

> **Python 3.6 注意事项**  
> Python 3.6 没有顶层函数 `asyncio.create_task`，可以改用：
>
> ```python
> t = asyncio.get_event_loop().create_task(
>     example_coroutine_function()
> )
> ```
>
> 两者作用相同，后者写法更冗长。

`create_task` 接收一个协程对象，返回继承自 `asyncio.Future` 的 `Task` 对象。调用会在当前线程的事件循环中创建任务，并安排它从协程代码块开头开始执行。只有任务执行完毕后，返回的 Future 才会变为 `done()`。

协程代码块的返回值会成为任务的 `result()`；若协程抛出异常，异常会被捕获并存入任务对应的 Future。

把协程包装为任务这一动作本身是同步调用，所以语法上可从同步或异步代码中执行：

- 在异步代码中，事件循环已经运行；当前任务下次暂停时，新任务可能获得执行机会。
- 在同步代码中，事件循环很可能还未运行。Python 文档不鼓励应用代码手工操纵事件循环。除非你在编写扩展 `asyncio` 的库，否则通常应避免从同步代码中直接创建任务。

若一个主要为同步代码的脚本只需要调用一次异步代码，可以使用 `asyncio.run()`。

## 运行异步程序

### 推荐方式：单一异步入口

把主要工作都写成协程，并用一个很简单的入口启动：

```python
import asyncio


async def get_data_from_io():
    ...


async def process_data(data):
    ...


async def main():
    while True:
        data = await get_data_from_io()
        await process_data(data)


asyncio.run(main())
```

`asyncio.run` 会建立事件循环、运行给定协程，并在结束时完成清理。现代应用通常应优先使用这种高层入口。

### 每次单独调用 `asyncio.run`

也可以把每一次协程调用分别包在 `run` 中：

```python
import asyncio


async def get_data_from_io():
    ...


async def process_data(data):
    ...


def main():
    while True:
        data = asyncio.run(get_data_from_io())
        asyncio.run(process_data(data))


main()
```

这种写法放弃了 `asyncio` 并发调度的大部分优势，但极少数简单脚本中可能仍然合适。

以上示例尚未充分利用多个任务交错运行的能力。随着经验增加，你会接触更完善的任务管理方式；这些基础已经足以起步。

## 手工操作事件循环（旧版 Python）

若使用 Python 3.6，并且需要从普通同步代码启动协程，就需要手动启动事件循环。

```python
asyncio.get_event_loop().run_forever()
```

这会让事件循环一直运行，直到被显式停止，通常用途有限。

更实用的是：

```python
r = asyncio.get_event_loop().run_until_complete(f)
```

若 `f` 是 Future（包括 Task），循环会一直运行到它完成，然后返回结果或抛出它保存的异常。

```python
async def example_coroutine_function():
    ...


loop = asyncio.get_event_loop()
t = loop.create_task(example_coroutine_function())
r = loop.run_until_complete(t)
```

这段代码创建任务，运行事件循环直到协程结束，再返回结果。还可以进一步简化：直接把协程对象传给 `run_until_complete`，它会自动替你调用 `create_task`。

这些低层做法主要用于旧版代码或库/框架开发；现代应用通常使用 `asyncio.run`。

## 怎样主动让出控制权

`asyncio` 没有一个单独名为 `yield_control` 的命令。一般也不需要显式让出控制权：程序会在等待底层异步 I/O 库返回的 Future 时自然切换任务。

不过在测试、调试或特定调度场景中，偶尔需要显式允许其他任务运行。惯用写法是：

```python
await asyncio.sleep(0)
```

它会暂停当前任务，让事件循环调度其他可运行任务。`asyncio.sleep(seconds)` 返回一个在指定秒数后完成的 Future。传入零秒时，不产生实际延时，但若有其他待运行任务，就会形成一次任务切换机会。

标准库对 `asyncio.sleep(0)` 做了优化，因此这是高效的操作。

当参数大于零时，要注意“Future 在指定时间后完成”并不等于“任务一定精确地在那个时刻恢复”。任务只能在事件循环没有执行其他任务时恢复，所以实际恢复时间可能晚于指定时间。

## 总结

- `await`、`async with`、`async for` 只能用于异步代码。
- 异步代码通常包含在 `async def` 声明中，而 `async def` 本身可以出现在任何允许 `def` 的位置。
- `await` 的操作数必须是：
  - 协程对象：协程函数调用的返回值；协程代码只有在被等待或包装成任务后才运行。
  - Future：代表别处正在进行、可能已完成的过程；等待它不会启动一段协程代码，但可能暂停当前任务。
  - 实现 `__await__` 的对象：行为由该对象的实现和文档决定。
- 可以把协程包装为 Task，使它被事件循环调度，并得到一个可用于检查状态、异常和结果的 Future。

对象关系可概括为：`Coroutine` 与 `Future` 都是 `Awaitable`；`Task` 是一种特殊的 `Future`。

### 完整示例

下面的程序只使用本文介绍的内容，创建四个任务，让它们交错打印 0～99：

```python
import asyncio


async def counter(name: str):
    for i in range(0, 100):
        print(f"{name}: {i!s}")
        await asyncio.sleep(0)


async def main():
    tasks = []
    for n in range(0, 4):
        tasks.append(asyncio.create_task(counter(f"task{n}")))

    while True:
        tasks = [t for t in tasks if not t.done()]
        if len(tasks) == 0:
            return

        await tasks[0]


asyncio.run(main())
```

每个任务打印一个数字后都会让出控制权，因而多个任务的输出会交错出现。这直观展示了 `asyncio` 如何让多项工作在单线程中穿插推进。
