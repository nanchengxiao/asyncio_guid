# Python Asyncio 中文完整指南

本文件合并 BBC R&D Cloudfit 团队的五篇 `asyncio` 教学文章中文译本。分篇版本见同目录。

---

# Python Asyncio（1）：基本概念与运行模式

> 原文：**Python Asyncio Part 1 – Basic Concepts and Patterns**  
> 来源：https://bbc.github.io/cloudfit-public-docs/asyncio/asyncio-part-1.html  
> 中文翻译整理日期：2026-07-25  
> 说明：代码与 API 名称尽量保持原样；文中版本描述反映原文写作时的 Python 生态。

自 Python 3.5 引入以来，`asyncio` 一直让不少程序员感到困惑。即便它在 Python 3.6 中获得了显著改进，并在 3.7、3.8 中持续演进，这个库仍常被误解和误用。

造成这种情况的一个原因是：Python.org 上的官方文档虽然非常详尽、准确，却不算容易通读，尤其对缺少 Python 异步编程经验的开发者而言更是如此。

我在 BBC R&D 的 Cloudfit 项目中开始使用 `asyncio` 时，发现网上缺少真正帮助我正确理解它的教程。基础语法入门文章不少，但面向有经验的 Python 程序员、能够填补“简单教程”和“完整库文档”之间空白的内容却很少。本系列文章正是为了填补这个空白。

## 本篇内容

本文讨论 `asyncio` 背后的基本概念，而不深入实现细节。有些读者已经熟悉这些概念，有些则没有。后续文章会介绍怎样在 Python 中真正使用 `asyncio`；但在进入语法与 API 之前，先建立正确的概念模型非常重要。

本篇的代码示例是全系列最少的，不过作者用若干示意图进行了补充。

## 一次只做一件事，但不必按固定顺序

介绍 `asyncio` 时，首先必须说明它是做什么的，更要说明它**不**是做什么的。

传统上，计算机一次只做一件事。现代计算机（以原文写作时的 2020 年为背景）通常配有多个 CPU 核心，因此可以同时做多件事。也有大量书籍、文章、库和框架讲解如何利用多个执行线程并行完成工作。

**`asyncio` 并不是其中之一。**

在 Python 代码中使用 `asyncio`，不会自动把代码变成多线程；它不会让多条 Python 指令同时执行，也不会让你绕过所谓的全局解释器锁（GIL）。这并不是 `asyncio` 的用途。

> **术语：CPU 密集型与 I/O 密集型**  
> 有些过程是 **CPU 密集型（CPU-bound）**：它们主要由一连串必须依次执行的计算指令组成，运行时会持续占用计算机的处理能力。  
> 另一些过程是 **I/O 密集型（I/O-bound）**：它们花大量时间与外部设备或进程收发数据，经常需要启动一个操作，然后等待它完成。等待期间，程序本身通常没有多少事情可做。

当程序执行 I/O 密集型代码时，CPU 经常因为当前工作正在等待外部响应而处于空闲状态。与此同时，程序里常常还有其他不依赖当前结果的工作可以继续。

`asyncio` 的目的，就是让你把代码组织成这样：当一段线性的单线程代码（称为**协程**）正在等待时，另一段协程可以接管 CPU 并继续执行。

**它不是为了使用多个核心，而是为了更有效地使用一个核心。**

## 子程序与协程

> **术语说明**  
> 各种编程语言会用 function、method、procedure、subroutine 等词表示可被其他代码调用的一段代码。下文大体沿用 Python 的习惯，主要使用“函数”和“方法”。

从抽象层面看，大多数编程语言中的函数调用遵循“子程序（subroutine）”模型：

1. 调用函数时，执行流跳到函数开头。
2. 一直执行到函数结束或遇到 `return`。
3. 然后回到调用点之后继续。
4. 此后再次调用该函数，会从头开始，且与前一次调用相互独立。

另一种执行模型叫作“协程（coroutine）”调用模型。协程除了 `return` 之外，还可以通过“让出（yield）”控制权回到调用者。协程让出控制权后，执行流回到调用点之后；但下次恢复该协程时，不会从开头重来，而会从上次暂停的位置继续。

因此，控制权可以在调用代码与协程代码之间来回切换。

![子程序与协程调用模式对比](assets/SubVsCoRoutines.png)

Python 很早就通过生成器（Generator）支持这种执行模型；`asyncio` 又引入了适合异步 I/O 的协程形式，使当前协程发生阻塞时，执行流能够自然地转移到其他协程。

## 栈与栈帧快速复习

多数操作系统和编程语言都使用“栈机器”这一抽象。除非你做过非常底层的汇编编程，否则你写过的绝大多数程序都依赖这种机制。它使一段代码能够“调用”另一段代码。

以这段 Python 代码为例：

```python
def a_func(x):
    return x - 2


def main():
    some_value = 12
    some_other_value = a_func(some_value)


main()
```

程序开始执行时，栈被初始化为空的后进先出（LIFO）内存区域，执行从最后一行 `main()` 开始。

原文图示：[`Stack0.svg`](https://bbc.github.io/cloudfit-public-docs/images/asyncio/Stack0.svg)

由于这一行是函数调用，Python 解释器会：

1. 在栈顶增加一个新的“栈帧（frame）”。它可以理解为容纳此次调用相关栈数据的结构。
2. 在栈帧中加入“返回指针”，告诉解释器函数返回后应从哪里恢复执行。
3. 把下一条待执行指令移到函数的第一行。

原文图示：[`Stack1.svg`](https://bbc.github.io/cloudfit-public-docs/images/asyncio/Stack1.svg)

下一条指令 `some_value = 12` 创建了函数调用上下文中的局部变量，因此这个变量被保存在该函数调用的栈帧内。

原文图示：[`Stack2.svg`](https://bbc.github.io/cloudfit-public-docs/images/asyncio/Stack2.svg)

接下来执行 `some_other_value = a_func(some_value)`，解释器再次执行函数调用流程：

1. 在栈顶加入新的栈帧。
2. 在新栈帧中放入返回指针，它指向 `main` 中调用完成后的下一条指令。
3. 将传入函数的参数放入栈帧中；参数本质上也是局部变量。
4. 把执行流移到 `a_func` 的第一行。

原文图示：[`Stack3.svg`](https://bbc.github.io/cloudfit-public-docs/images/asyncio/Stack3.svg)

下一条指令是 `return x - 2`，解释器执行函数返回流程：

1. 从栈中移除最上方的栈帧及其中的所有内容。
2. 将函数返回值放到栈顶。
3. 根据被移除栈帧里的返回指针恢复执行。

原文图示：[`Stack4.svg`](https://bbc.github.io/cloudfit-public-docs/images/asyncio/Stack4.svg)

几乎所有传统编程语言中的代码都遵循这种模式。多线程程序的主要变化，是每个线程有自己的栈；除此之外，基本机制相同。

但 `asyncio` 的工作方式略有不同。

## 事件循环、任务与协程

在 `asyncio` 的世界里，不再只是“每个线程一个栈”。每个线程中会有一个叫作**事件循环（Event Loop）**的对象。如何创建、使用和关闭事件循环会在第 2 篇介绍；这里先假设它已经存在。

事件循环内部维护一组称为**任务（Task）**的对象。每个任务都维护自己的栈和执行位置。

原文图示：[`EventLoop.svg`](https://bbc.github.io/cloudfit-public-docs/images/asyncio/EventLoop.svg)

任意时刻，事件循环中只能有一个任务真正在执行；处理器毕竟一次仍只能执行一件事。循环里的其他任务处于暂停状态。

当前任务会像普通同步 Python 程序中的函数一样持续执行，直到它走到某个必须等待外部事件发生才能继续的位置。

此时，任务中的代码不会原地阻塞等待，而是**让出控制权**：它请求事件循环暂停当前任务，并在所等待的事情完成后再将其唤醒。

事件循环随后可以选择另一个可运行的任务，将它唤醒并设为当前执行任务。如果所有任务都在等待外部事件，事件循环本身便等待，直到其中某个任务具备继续运行的条件。

这样，CPU 时间便能在多个任务之间共享；每个任务在本来需要等待时都可以主动让出控制权。

> **重要：事件循环不能强行打断正在执行的协程。**  
> 一个协程一旦开始执行，就会一直运行到它主动让出控制权。事件循环负责挑选下一项要调度的协程，并记录哪些协程因等待 I/O 而暂时不能运行；但这些调度工作只能在当前没有协程正在执行时进行。

控制权在不同任务之间来回移动，并在每次恢复时从任务上次停止的位置继续，这种执行模式就是协程调用。`asyncio` 把它带入 Python，目的是让 CPU 因等待 I/O 而空闲的时间更少。

> **重要：这种方式最适合 I/O 密集型代码。**  
> I/O 密集型程序经常会长时间等待其他设备或计算机回应。任何处理 HTTP 或其他网络协议流量的程序，几乎都必然包含大量 I/O 等待。

## 那么，在 Python 中具体怎样实现？

到这里，本文几乎已经结束，却还没有给出一段真正调用 `asyncio` 的代码。这是有意为之：本篇先建立抽象模型。

实际语法，以及开发普通 `asyncio` 应用时最有用的接口，会在下一篇中介绍：**Python Asyncio（2）：可等待对象、任务与 Future**。

---

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

---

# Python Asyncio（3）：异步上下文管理器与异步迭代器

> 原文：**Python Asyncio Part 3 – Asynchronous Context Managers and Asynchronous Iterators**  
> 来源：https://bbc.github.io/cloudfit-public-docs/asyncio/asyncio-part-3.html  
> 中文翻译整理日期：2026-07-25  
> 说明：代码与 API 名称尽量保持原样；版本描述反映原文写作和后续修订时的状态。

前两篇已经介绍了 `asyncio` 的基本概念和基本语法。本篇详细讲解两个经常出现在异步库接口中的语言特性：**异步上下文管理器**与**异步迭代器**。要熟练使用 `asyncio` 生态中的库，理解它们几乎不可或缺。

许多示例来自 BBC R&D Cloudfit 项目中实际使用过的代码。

## 异步上下文管理器

有经验的 Python 程序员通常熟悉上下文管理器，也可能编写过自己的上下文管理器来简化资源管理。异步上下文管理器是这个概念在异步环境中的自然扩展，在 `asyncio` 库接口中非常常见。

异步上下文管理器是能够用于 `async with` 语句的对象：

```python
async with FlowProvider(store_url) as provider:
    async with provider.open_read(flow_id, config=config) as reader:
        frames = await reader.read(720, count=480)

        # 使用 reader 做其他事情
        ...

    # 使用 provider 做其他事情
    ...

# 在上下文之外继续使用 frames
...
```

这里，`FlowProvider` 返回一个异步上下文管理器，`provider.open_read` 也返回一个异步上下文管理器。概念上，代码依次完成：

1. 为 `FlowProvider` 执行资源获取或初始化，并把结果绑定到 `provider`。
2. 为 `provider.open_read` 执行额外的资源获取或初始化，并把结果绑定到 `reader`。
3. 在内部代码块中使用 `reader`，例如等待 `reader.read` 返回帧列表。
4. 执行其他依赖 `reader` 的操作。
5. 内层代码块结束后，对 `reader` 执行清理和资源释放。
6. 执行其他依赖 `provider` 的操作。
7. 外层代码块结束后，对 `provider` 执行清理和资源释放。
8. 离开两个上下文后，`reader` 和 `provider` 所管理的资源已经清理，但 `frames` 等变量仍然可访问并保留其值。

这种结构与同步 `with` 的用途相同：把“进入资源上下文—使用资源—可靠退出与清理”表达为一个清晰的代码块。

> **实用建议**  
> 如果某个对象在使用前需要特定设置，或者使用结束后必须执行特定操作，就把它设计成上下文管理器，用它包围真正使用该对象的代码。  
> 如果设置或关闭过程涉及 I/O，就把它设计成异步上下文管理器，使这些 I/O 能够异步完成。

需要注意，`FlowProvider` 和 `provider.open_read` 本身**不是协程函数**。它们是普通同步方法，只是返回异步上下文管理器对象。这是很常见的设计；反而很少见到“协程返回一个异步上下文管理器，再由调用者等待后使用”的两阶段接口。

> **类型提示**  
> `typing` 提供 `AsyncContextManager[T]` 抽象类型，其中 `T` 是 `async with ... as ...` 中 `as` 子句绑定对象的类型。

### `async with` 的展开形式

`async with` 本质上是包含若干 `await` 的语法糖：

```python
async with AsyncCM as ctx:
    ...

# 大致等价于：
ctx = await AsyncCM.__aenter__()
try:
    ...
except Exception as e:
    if not await AsyncCM.__aexit__(type(e), e, e.__traceback__):
        raise e
else:
    await AsyncCM.__aexit__(None, None, None)
```

因此，自定义异步上下文管理器时，只需在类中实现两个魔术协程方法：

```python
async def __aenter__(self):
    ...


async def __aexit__(self, exc_t, exc_v, exc_tb):
    ...
```

它们的参数与返回值规则如下：

- `__aenter__` 可以返回任意对象。这个返回值会绑定到 `async with` 的 `as` 子句。
- 若 `async with` 的代码块正常结束，`__aexit__` 的三个参数都会是 `None`，其返回值被忽略。
- 若代码块抛出异常，`__aexit__` 会收到异常类型、异常对象和 traceback 对象。
- 若异常情况下 `__aexit__` 返回 `True` 或其他真值，系统认为异常已被处理，不再继续传播。
- 若返回 `False`、`None`、其他假值，或没有显式返回值，异常会继续向外传播。

### 同时提供同步和异步接口

一个类可以同时实现 `__enter__`/`__exit__` 与 `__aenter__`/`__aexit__`，从而既可作为同步上下文管理器，也可作为异步上下文管理器。这能形成很清晰的双接口：

```python
# 同步执行 I/O
with RemoteResource(*some_parameters) as connection:
    connection.send(some_data)
    new_data = connection.recv()

# 异步执行相同的 I/O
async with RemoteResource(*some_parameters) as connection:
    await connection.send(some_data)
    new_data = await connection.recv()
```

这种设计使同步与异步调用方式容易辨认，也方便调用者根据运行环境切换。

### 使用 `@asynccontextmanager`

定义异步上下文管理器还有更简洁的办法：使用 `@asynccontextmanager` 装饰器。Python 3.7 及以上版本在标准库 `contextlib` 中提供它；原文指出，在 Python 3.6 中可以通过 PyPI 的 `async_generator` 包获得类似功能。

```python
from contextlib import asynccontextmanager


@asynccontextmanager
async def ExampleAsyncCM(a_param, b_param):
    # 相当于 __aenter__ 中的设置过程
    ...

    yield obj  # obj 会绑定给 as 子句

    # 相当于 __aexit__ 中的清理过程
    ...
```

`yield` 之前的代码负责进入上下文，`yield` 的值交给 `as`，`yield` 之后的代码负责退出上下文。

若 `async with` 的代码块抛出异常，那么对于这种用装饰器定义的上下文管理器，异常会在 `yield` 语句处重新抛出。你可以围绕 `yield` 使用 `try`/`except`/`finally`，实现与 `__aexit__` 相同的异常处理和可靠清理逻辑。

## 异步迭代器

迭代器与生成器是 Python 中非常常见的工具。异步迭代器和异步生成器是它们在异步环境中的自然对应物，就像异步上下文管理器对应普通上下文管理器一样。

抽象地说：

- **可迭代对象（iterable）**表示可由普通 `for` 循环逐项读取的数据源。
- **异步可迭代对象（async iterable）**表示可由 `async for` 循环逐项读取的数据源，而获取下一项的过程可以包含异步等待。

使用方式很直接：

```python
async for grain in reader.get_grains():
    # 逐个处理 grain 对象
    ...
```

`reader.get_grains` 返回异步可迭代对象。循环每次从它派生的异步迭代器中取出一个元素，并绑定给局部变量 `grain`。与普通 `for` 的区别在于，异步迭代器“取下一项”的方法是协程，其结果需要等待。

### `async for` 的展开形式

```python
async for a in async_iterable:
    await do_a_thing(a)

# 大致等价于：
it = async_iterable.__aiter__()
while True:
    try:
        a = await anext(it)
    except StopAsyncIteration:
        break

    await do_a_thing(a)
```

因此，和 `await`、`async with` 一样，`async for` 只能用于允许异步代码的上下文，例如 `async def` 定义的协程函数体。

> **版本说明**  
> 内置写法 `anext(async_iterator_object)` 在 Python 3.10 中加入，类似普通迭代器的 `next(iterator_object)`。在 Python 3.9 或更早版本中，需要直接写：
>
> ```python
> await async_iterator_object.__anext__()
> ```

> **实用场景**  
> 异步迭代器很适合表示远程资源：每拉取一个对象都可能需要耗时 I/O。  
> 协程并非每次被等待都会真正暂停，因此异步迭代器还能隐藏优化后的预取策略：在后台通过任务预加载数据，只有调用者需要的对象尚未准备好时才暂停当前任务。

### 实现异步可迭代对象与异步迭代器

异步可迭代对象需要实现：

```python
def __aiter__(self):
    ...
```

它返回一个异步迭代器。注意：`__aiter__` **不是协程方法**。

异步迭代器则实现：

```python
def __aiter__(self):
    return self


async def __anext__(self):
    ...
```

其中：

- `__aiter__` 返回自身；
- `__anext__` 是协程方法，每次被等待时返回下一项；
- 没有更多元素时，应通过 `StopAsyncIteration` 表示迭代结束。

> **注意**  
> 虽非强制要求，但通常会让自定义异步可迭代对象每次调用 `__aiter__` 时都返回一个新的异步迭代器，使每次迭代从序列开头重新开始。

> **类型提示**  
> `typing.AsyncIterable[T]` 和 `typing.AsyncIterator[T]` 可用于标注异步可迭代对象和异步迭代器。

手工编写异步迭代器仍比普通生成器麻烦，因此 Python 也提供了异步生成器作为简写。

## 异步生成器

异步生成器是定义异步迭代器的简便方式。它还有超出迭代器接口的高级用途，但这些用法较少见。

异步生成器函数同样用 `async def` 声明，不过函数体中至少包含一个 `yield`：

```python
async def async_generator_method_example(param):
    ...
    ...

    yield something

    ...
    ...

    yield something_else

    ...
    ...  # 等等
```

> **重要**  
> 异步协程函数和异步生成器函数在声明行上没有区别；唯一决定因素是函数体内是否存在 `yield`。两者的使用方式却完全不同，因此不容易一眼分辨。

建议用名称、注释、文档字符串、类型标注等方式明确指出某个函数是异步生成器，语言语法本身不会替你突出这一点。

异步生成器函数的调用是同步的，它返回一个异步生成器对象；它**不是协程函数**，因此不能等待它的返回值：

```python
async def coroutine_method():
    return 3


async def generator_method():
    yield 3


# 正确
r = await coroutine_method()

# 会抛出异常
r = await generator_method()
```

但异步生成器对象是异步迭代器，因此可用于 `async for`：

```python
# 合法，并会打印 3
async for r in generator_method():
    print(r)
```

对于异步生成器对象 `g`：

1. 第一次等待 `g.__anext__()` 时，生成器代码从开头运行到第一个 `yield`，或运行到函数结束。
2. `yield` 后面的值成为这次等待的结果。
3. 下一次等待 `g.__anext__()` 时，代码从上次 `yield` 的位置继续，直到下一个 `yield`。
4. 若函数执行到 `return` 或代码块末尾，等待 `g.__anext__()` 会抛出 `StopAsyncIteration`，`async for` 捕获它并正常结束循环。

> **警告**  
> 虽然在异步生成器内部直接抛出 `StopAsyncIteration` 可能在某些语境中看似合理，但不推荐这样做，代码会难以理解，部分静态检查器也会把它视为错误。应使用 `return` 结束生成器。异步生成器的 `return` 不能携带返回值，否则是语法错误。

### 高级异步生成器：双向传值

异步生成器的 `yield` 不仅能产出值，还能接收调用者送回的值：

```python
async def advanced_generator(y):
    for i in range(0, 10):
        x = await do_something(y)
        y = yield x
```

这超出了普通 `async for` 接口，需要显式驱动生成器：

```python
it = advanced_generator(first_y)
x = await anext(it)

while True:
    y = await do_something_else(x)
    try:
        x = await it.asend(y)
    except StopAsyncIteration:
        break
```

执行过程如下：

1. 调用 `advanced_generator(first_y)` 创建生成器，初始参数 `y` 为 `first_y`。
2. 第一次 `anext(it)` 启动生成器，等待 `do_something(y)`，然后通过 `yield x` 把 `x` 交回调用者。
3. 调用者用该 `x` 执行 `do_something_else(x)`，得到新的 `y`。
4. `it.asend(y)` 把这个值送回生成器；它成为生成器中 `yield x` 表达式的结果，并赋给 `y`。
5. 双方如此来回传值，直到生成器结束并抛出 `StopAsyncIteration`。

这种模式可以构建复杂的双向异步数据流，不过大多数应用不需要它。

## 异步推导式

有时连显式编写生成器都显得冗长。Python 提供了异步生成器推导式，它是普通生成器推导式的异步版本。

基本形式为：

```python
it = (
    <async_expression>
    async for <variable> in <async_iterable>
    if <condition>
)
```

它大致等价于：

```python
async def _gen():
    async for <variable> in <async_iterable>:
        if <condition>:
            yield <async_expression>


it = _gen()
```

`if <condition>` 可以省略。它让你用一行表达式基于一个异步可迭代对象创建另一个异步生成器。

`<async_expression>`、`<async_iterable>` 和 `<condition>` 内部都可以包含异步表达式，因为它们最终会嵌入异步生成器的函数体。关键在于：推导式本身只创建生成器对象，不立即执行其中的异步代码，所以异步生成器推导式甚至可以出现在同步函数中：

```python
def sync_method(gen):
    # 这是同步方法
    ...
    it = (
        await x.run()
        async for x in gen
        if not (await x.skip())
    )
    ...
    return it
```

乍看之下，代码似乎在同步函数中写了 `await`，但这些等待表达式属于将来才运行的异步生成器体，因此语法上有效。

### 异步列表推导式

另一种外观非常相似的结构是异步列表推导式：

```python
l = [
    <async_expression>
    async for <variable> in <async_iterable>
    if <condition>
]
```

它大致等价于：

```python
async def _list():
    r = []
    async for <variable> in <async_iterable>:
        if <condition>:
            r.append(<async_expression>)
    return r


l = await _list()
```

与异步生成器推导式不同，列表推导式会立即迭代并构建完整列表，相当于创建并等待一个协程。因此它只能出现在允许 `await` 的异步上下文中。

异步集合推导式和异步字典推导式也可用相同方式构造；和列表推导式一样，它们必须用于异步代码中。

## 总结

本文快速介绍了异步上下文管理器、异步可迭代对象、异步迭代器、异步生成器和异步推导式。

最重要的结论是：

- **异步上下文管理器非常实用**，广泛存在于异步库接口中；正确理解和使用 `async with` 很重要。
- 异步迭代器及相关结构不如上下文管理器常见，但仍会不时遇到。即使不能随时背出所有魔术方法，也应知道这些机制存在，并能在需要时查阅。

到这里，Python `asyncio` 的基本工具、语言特性和语法已经介绍完毕。下一篇将转向标准库与 PyPI 中的实用支持库。

---

# Python Asyncio（4）：库支持

> 原文：**Python Asyncio Part 4 – Library Support**  
> 来源：https://bbc.github.io/cloudfit-public-docs/asyncio/asyncio-part-4.html  
> 中文翻译整理日期：2026-07-25  
> 说明：代码、库名与 API 名称尽量保持原样；文中“截至 2020 年 8 月”等表述属于原文历史背景，具体版本兼容性请以当前项目文档为准。

前三篇介绍了 `asyncio` 的基本概念、基础语法和几个较高级的语言特性。本篇转换重点，快速浏览一些真正能用来完成工作的实用库，并给出代码示例。这些库都曾用于 BBC R&D 的 Cloudfit 项目。

其中包括少量 Python 标准库功能，但主要讨论第三方库。本文不会深入介绍标准库中较底层的 Transport 和 Protocol；它们更适合编写扩展 `asyncio` 的库或框架，而不是大多数普通应用程序。

## 使用 `aiohttp` 发起 HTTP 请求

[`aiohttp`](https://docs.aiohttp.org/) 用于通过 `asyncio` 方便地处理 HTTP 协议。它同时支持客户端和服务端；这里重点介绍客户端。

熟悉同步 HTTP 库 `requests` 的开发者会觉得 `aiohttp` 的接口比较亲切，因为它的设计与 `requests` 有不少相似之处。

最基本的请求示例：

```python
import aiohttp
import asyncio


async def main():
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(
            "https://www.bbc.co.uk/rd/projects/cloud-fit-production"
        ) as resp:
            print(resp.status)
            print(await resp.text())


asyncio.run(main())
```

关键点是：

1. 创建 `ClientSession`，并把它作为异步上下文管理器进入。
2. 每个请求本身也作为异步上下文管理器进入。
3. 在请求上下文中，通过响应对象的成员读取数据；读取正文等操作通常需要 `await`。
4. 离开上下文时，响应和会话能够正确清理资源。

`aiohttp` 支持 GET、OPTIONS、PUT、POST、HEAD、DELETE 等请求方法，也支持自定义请求头、认证、HTTPS 等功能。

### WebSocket

`aiohttp` 还内置 WebSocket 支持：

```python
import aiohttp
import asyncio


async def main():
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.ws_connect(
            "wss://echo.websocket.org/"
        ) as ws:
            n = 0
            print(f"Sending 'hello{n}'")
            await ws.send_str(f"hello{n}")

            async for msg in ws:
                print(f"Received '{msg.data}'")

                print(f"Sending 'hello{n}'")
                await ws.send_str(f"hello{n}")

                n += 1
                if n == 10:
                    return


asyncio.run(main())
```

连接作为异步上下文管理器使用；收到的消息流则作为异步迭代器使用。若运行环境位于 HTTPS 代理后面，原文提醒可能需要在 `ws_connect` 调用中设置 `proxy` 关键字参数。

截至原文写作时，HTTP 请求已经是程序执行 I/O 的最常见方式之一。许多程序会发出大量请求以获取数据、提交结果，并在中间执行 CPU 密集型处理。如何在 `asyncio` 程序中处理 CPU 密集型操作，会在第 5 篇讨论。

使用 `aiohttp` 以及大多数其他 I/O 库时，通常应该保留一个较长生命周期的会话对象。常见做法是把它设计成异步上下文管理器，在程序启动附近进入，在程序退出时才离开，而不是为每个请求重复创建和销毁会话。

### 请求重试：`aiohttp_retry`

原文还推荐了 [`aiohttp_retry`](https://github.com/inyutin/aiohttp_retry)。它提供异步上下文管理器，在遇到临时性错误时自动重试 HTTP 请求。

Cloudfit 在长时间发起大量 HTTP 请求时使用这类机制，以处理偶发的服务器错误和网络抖动。重试策略应考虑幂等性、退避时间、最大次数以及不可重试错误，不能无条件无限重试。

## 使用 `AsyncExitStack` 管理多个上下文管理器

编写 `asyncio` 程序时，经常需要自定义异步上下文管理器来封装某些操作所需的运行环境。进入一个自定义上下文时，可能还需要按顺序进入多个其他同步或异步上下文；退出时则要反向退出，并正确传播或处理异常。

只有一个内层异步上下文管理器时，可以手工写成：

```python
class CustomACM(object):
    async def __aenter__(self):
        self.__inner_acm = InnerACM(...)
        self.__inner_acm_ctx = await self.__inner_acm.__aenter__()

        # 为本类执行更多设置
        ...

    async def __aexit__(self, exc_t, exc_v, exc_tb):
        if exc_v is None:
            try:
                # 成功时执行自定义清理
                ...
            except Exception as e:
                (exc_t, exc_v, exc_tb) = (
                    type(e), e, e.__traceback__
                )
        else:
            # 失败时执行自定义清理
            ...

        return await self.__inner_acm.__aexit__(
            exc_t, exc_v, exc_tb
        )
```

这可以工作。但当需要管理多个上下文时，代码很快变得难以维护：某一步抛出异常后，哪些资源已经进入、哪些需要退出、异常应传给后续哪个 `__aexit__`、哪个退出方法已经吞掉异常，都需要谨慎处理。

### 使用嵌套的 `async with`

在较简单的场景中，可把自定义上下文管理器定义成：

```python
from contextlib import asynccontextmanager


@asynccontextmanager
async def CustomACM():
    async with InnerACM1() as inner1:
        async with InnerACM2() as inner2:
            # 自定义设置
            ...

            try:
                yield
            except Exception as e:
                # 失败时清理
                ...
                raise e
            else:
                # 成功时清理
                ...
```

但若这个类除了充当上下文管理器还要提供其他方法，或需要更细粒度地控制行为，单纯的生成器式上下文管理器并不总是合适。

### `contextlib.AsyncExitStack`

`AsyncExitStack` 正是为这种问题设计的。原文说明，它在 Python 3.7 中加入标准库 `contextlib`；更早版本可使用 PyPI 上的 `async_exit_stack` 包。

它把多个同步和异步上下文管理器包装成一个异步上下文管理器。退出最外层栈时，它会按照正确的逆序展开所有资源，并正确地把异常传递给各个退出方法。

```python
from contextlib import AsyncExitStack


class CustomACM(object):
    def __init__(self):
        self._exit_stack = AsyncExitStack()

    async def __aenter__(self):
        await self._exit_stack.__aenter__()

        self.__inner1 = await self._exit_stack.enter_async_context(
            InnerACM1()
        )
        self.__inner2 = await self._exit_stack.enter_async_context(
            InnerACM2()
        )
        self.__inner3 = self._exit_stack.enter_context(
            InnerCM()
        )
        self.__inner4 = await self._exit_stack.enter_async_context(
            InnerACM3()
        )
        return self

    async def __aexit__(self, exc_t, exc_v, exc_tb):
        return await self._exit_stack.__aexit__(
            exc_t, exc_v, exc_tb
        )

    # 其他方法可使用 self.__inner<n> 属性
    ...
```

这个类进入时依次进入一系列异步与同步上下文管理器，然后通过自定义方法使用这些资源。异常情况下不需要再写大量分支来手工清理，因为退出栈会替你完成正确的展开。

> **注意**  
> 如果除了进入其他上下文，还要执行额外的自定义初始化，可以为这部分单独创建一个很小的异步上下文管理器。让它假设外部资源已经进入，并把外部上下文返回值作为参数传入，能够保持主 `CustomACM` 类简洁。

## 单元测试

原文说明，Python 标准库 `unittest` 在 Python 3.9 时已经提供异步测试支持；在 Python 3.8 或更早环境中，可查找当时的 `AsyncTest` 等方案。现代代码应查看当前版本中 `unittest.IsolatedAsyncioTestCase` 的文档。

测试类继承 `unittest.IsolatedAsyncioTestCase` 后，测试方法可以是协程函数。还可使用 `asyncSetUp` 和 `asyncTearDown`，并与传统的 `setUp`、`tearDown` 配合。

```python
import unittest
from stuff import do_sync_stuff, do_async_stuff


expected_value = 1


class TestStuff(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # 异步测试设置
        ...

    def test_synchronous(self):
        r = do_sync_stuff()
        self.assertEqual(r, expected_value)

    async def test_asynchronous(self):
        r = await do_async_stuff()
        self.assertEqual(r, expected_value)
```

这里包含两个测试：一个同步执行，另一个异步执行。

### `AsyncMock`

`unittest.mock` 提供 `AsyncMock`，用于模拟协程函数。它可以看作面向异步调用的 `MagicMock`，并能适当地响应许多魔术方法。

> **重要**  
> `AsyncMock` 的实例是**可调用的模拟对象，表现得像协程函数**，而不是已经创建好的协程对象。它非常适合最常见的异步函数调用。  
> 若要模拟“把协程对象或 Future 当作值传来传去”等更复杂模式，可能需要从 `MagicMock` 开始自己构造模拟对象，不过一般并不困难。

原文还链接了该站点的 *Unit Testing Python Asyncio Code*，提供更详细的异步测试说明。

## 模拟异步上下文管理器和异步迭代器

模拟这两类对象有两种主要方式：

1. **自动规格（auto-speccing）**；
2. 自己实现相应的魔术方法。

### 自动规格

向 Mock 提供一个包含所需接口的真实类或规格类。自动规格机制会检查类中的方法是普通函数还是协程函数，并在需要时分别生成 `MagicMock` 或 `AsyncMock`。

原文指出，Python 文档中的入门示例很有帮助，但其中某些异步生成器示例带有额外的 Mock “魔法”：例如给 `mock.__aiter__.return_value` 赋值时，框架会做一些不完全显式的适配。使用时应通过测试确认模拟对象确实遵循生产代码所依赖的协议。

### 手工实现魔术方法

若自动规格不适合当前场景，也可以直接为模拟对象创建异步生成器或上下文管理器所需的魔术方法。务必根据方法协议选择正确的 Mock 类型：

- 非协程方法，如 `__aiter__`，通常使用 `MagicMock`；
- 协程方法，如 `__anext__`、`__aenter__`、`__aexit__`，通常使用 `AsyncMock`。

第 3 篇对这些方法哪些是同步、哪些是异步给出了详细说明。

## 总结

本文只触及了 `asyncio` 支持库的表面，但 HTTP 客户端、测试工具以及简化资源管理的标准库工具，已经覆盖许多典型需求。

若要访问 HTTP 之外的 I/O 协议，例如 SQL 数据库连接，通常也能找到结构相似的异步库：它们往往通过异步上下文管理器管理连接生命周期，通过协程执行单次操作，并可能通过异步迭代器流式返回结果。

---

# Python Asyncio（5）：混合同步与异步代码

> 原文：**Python Asyncio Part 5 – Mixing Synchronous and Asynchronous Code**  
> 来源：https://bbc.github.io/cloudfit-public-docs/asyncio/asyncio-part-5.html  
> 中文翻译整理日期：2026-07-25  
> 说明：代码、API 名称与历史版本表述尽量保持原意。为使 `run_in_executor` 示例符合其 API 签名，译文显式写出了默认执行器参数 `None`。

前几篇已经介绍了 `asyncio` 的基本概念、基础语法、若干高级特性和一些有用的库。本篇重新深入接口细节，讨论怎样在同一项目中组合同步与异步代码。

BBC R&D 的 Cloudfit 项目多次遇到这种需求，尤其是在必须使用尚未直接支持 `asyncio` 的既有库时。

## 一件做不到的事，以及一件不该做的事

没有事件循环，就无法真正运行异步代码；除非自己实现某种特殊替代机制来模拟事件循环。因此，在一个没有运行中事件循环的程序里等待协程，意味着你必须先启动事件循环。幸运的是，应用代码通常只需要在顶层入口处理一次这个问题。

反过来，从异步代码调用普通同步代码非常容易，而且语法上完全允许。但若某个同步函数可能“阻塞”——也就是很久以后才返回——就不应该直接在事件循环线程中调用它。

问题可以用以下代码清楚地展示：

```python
import requests
import asyncio
import time


async def counter():
    now = time.time()
    print("Started counter")
    for i in range(0, 10):
        last = now
        await asyncio.sleep(0.001)
        now = time.time()
        print(f"{i}: Was asleep for {now - last}s")


async def main():
    t = asyncio.get_event_loop().create_task(counter())
    await asyncio.sleep(0)

    print("Sending HTTP request")
    r = requests.get("http://example.com")
    print(f"Got HTTP response with status {r.status_code}")

    await t


asyncio.get_event_loop().run_until_complete(main())
```

运行结果大致如下：

```text
Started counter
Sending HTTP request
Got HTTP response with status 200
0: Was asleep for 0.019963502883911133s
1: Was asleep for 0.0012884140014648438s
2: Was asleep for 0.0012254714965820312s
3: Was asleep for 0.0011649131774902344s
4: Was asleep for 0.0011239051818847656s
5: Was asleep for 0.0012202262878417969s
6: Was asleep for 0.0012269020080566406s
7: Was asleep for 0.001184701919555664s
8: Was asleep for 0.0011556148529052734s
9: Was asleep for 0.00115203857421875s
```

可以看到，计数器在 HTTP 请求执行期间完全停住。`requests.get` 是普通同步 I/O 调用，只有请求完成后才返回。它不是异步代码，事件循环无法在其中途打断它并调度其他任务，所以它在整个执行期间都“阻塞了事件循环”。

这显然是个问题。

> **注意：CPU 密集型工作也会阻塞事件循环**  
> 除同步阻塞 I/O 外，另一类很容易阻塞事件循环的工作是 CPU 密集型过程，即长时间持续计算、占满 CPU 的代码。例如训练神经网络、把原始视频压缩为 H.264、对大数据集执行一系列傅里叶变换等。

不过，有多种技术可以缓解，甚至完全消除这类阻塞。

## 执行器与多线程

`asyncio` 从根本上说是单线程技术。每个事件循环运行在一个线程上，把该线程的执行时间复用给不同任务。对于由 `asyncio` 感知型库实现的 I/O 密集型工作，这种模型非常高效。

但并非所有工作都是 I/O 密集型，也并非所有库都支持 `asyncio`。此时就需要多线程。

事件循环本身在单线程运行，并不意味着整个程序不能同时拥有其他线程。事实上，保留一个线程池非常有用：把耗时的阻塞工作提交到池中，让每次阻塞调用占用自己的工作线程，而事件循环线程继续服务其他协程。

`asyncio` 通过事件循环的 `run_in_executor` 方法支持这种模式：

```python
import requests
import asyncio
import time


async def counter():
    now = time.time()
    print("Started counter")
    for i in range(0, 10):
        last = now
        await asyncio.sleep(0.001)
        now = time.time()
        print(f"{i}: Was asleep for {now - last}s")


async def main():
    t = asyncio.get_event_loop().create_task(counter())
    await asyncio.sleep(0)

    def send_request():
        print("Sending HTTP request")
        r = requests.get("http://example.com")
        print(f"Got HTTP response with status {r.status_code}")

    await asyncio.get_event_loop().run_in_executor(
        None, send_request
    )

    await t


asyncio.get_event_loop().run_until_complete(main())
```

输出大致为：

```text
Started counter
Sending HTTP request
0: Was asleep for 0.0016489028930664062s
1: Was asleep for 0.0019485950469970703s
2: Was asleep for 0.0011708736419677734s
3: Was asleep for 0.00118255615234375s
4: Was asleep for 0.001283884048461914s
5: Was asleep for 0.001234292984008789s
6: Was asleep for 0.0011649131774902344s
7: Was asleep for 0.0012319087982177734s
8: Was asleep for 0.001219034194946289s
9: Was asleep for 0.001234292984008789s
Got HTTP response with status 200
```

这一次，HTTP 请求没有阻塞计数器任务。

### `run_in_executor` 的行为

`run_in_executor` 接收两个或更多参数，并返回 Future：

1. 第一个参数指定线程池或进程池。传入 `None` 时，使用事件循环拥有的默认线程池；多数场景下这正是所需选择。
2. 第二个参数是要在线程中执行的同步可调用对象。
3. 后续参数会作为位置参数传给该可调用对象。

工作线程中的函数执行完毕后，Future 变为完成状态：

- 若函数返回值，该值成为 Future 的结果；
- 若函数抛出异常，异常被保存到 Future 中，并在等待结果时重新抛出。

在许多场景中，可把 `run_in_executor` 返回的 Future 当作类似 `create_task` 返回值的对象来使用，但二者的执行位置不同：

- `create_task` 创建的任务在事件循环线程上与其他异步任务复用执行时间；
- `run_in_executor` 提交的同步函数在另一个线程或进程中执行，通常很快便开始运行。

用 `run_in_executor` 把阻塞调用包装到其他线程，是在 `asyncio` 程序中复用非异步库最简单的办法之一。仍需留意潜在问题，尤其是底层库是否线程安全；但大量同步代码都可通过这种方式包装成近似异步的接口。

它也可用于 CPU 密集型代码，不过需要结合 GIL 的特点选择线程池还是进程池。

> **历史类型标注说明**  
> 原文指出，一些旧版 Python 或旧版类型存根曾错误地把 `run_in_executor` 标成协程函数。它实际上一直是返回 Future 的普通方法。现代代码应以当前 Python 文档和类型存根为准。

## 全局解释器锁（GIL）会怎样影响执行器？

Python 的全局解释器锁是一个互斥锁。在同一个进程里，任何正在解释 Python 指令的线程都必须持有它。因此，通常不能让两个 Python 线程同时真正执行 Python 字节码，不过解释器可在指令之间频繁切换线程。

若 Python 方法调用了本地原生代码，执行期间通常会释放 GIL。因此，当多个线程中至多一个正在解释 Python 代码，而其他线程正在执行释放了 GIL 的原生代码时，它们可以真正并行推进。

Python 中实现阻塞 I/O 的底层本地代码会在等待期间释放 GIL。这意味着，在线程池中运行同步阻塞 I/O 时，该线程的等待不会锁死其他 Python 线程。

CPU 密集型工作则更复杂：

- 许多数值计算、压缩、机器学习等库会把重计算交给原生代码，并在计算时释放 GIL；这些库可能适合在线程池中运行。
- 若 CPU 密集型算法由纯 Python 实现，多个线程会竞争 GIL，频繁切换，导致其他任务变慢，无法获得真正的多核并行。

对于纯 Python 的 CPU 密集型任务，可以创建 `concurrent.futures.ProcessPoolExecutor`，并把它作为 `run_in_executor` 的第一个参数。代码将在另一个进程中执行，各进程不共享同一个 GIL，从而可以利用多个 CPU 核心。

## 反向调用：`run_coroutine_threadsafe`

少数情况下，你可能有一段运行在独立线程中的同步代码，需要调用另一个线程中事件循环上的异步代码。这时可以使用同步函数 `asyncio.run_coroutine_threadsafe`。

> **警告**  
> 这种技术只有在以下条件同时满足时才有用：当前代码是运行在一个线程上的同步函数，并且另一个线程中已经有事件循环在运行。  
> 若同步函数本身就在事件循环线程中，或者根本没有运行中的事件循环，就不能用它解决问题。

`run_coroutine_threadsafe` 接收两个参数：

1. 一个**协程对象**，不是协程函数、Future 或其他对象；
2. 目标事件循环对象。

调用会在目标循环中创建一个 Task 来包装协程，然后再把它包装成 `concurrent.futures.Future`。这个 Future 面向多线程环境，与 `asyncio.Future` 相似，但并不相同。

它同样提供 `done()`、`result()` 和 `exception()`。区别在于，若 Future 尚未完成：

- `asyncio.Future.result()` / `.exception()` 会抛出状态错误；
- `concurrent.futures.Future.result()` / `.exception()` 默认会阻塞当前线程，直到 Future 完成，也可结合超时参数使用。

因此，从同步线程的角度看，在 `concurrent.futures.Future` 上调用 `result()`，很像异步任务在 `asyncio.Future` 上执行 `await`：两者都会等到结果准备好，只是一个阻塞线程，另一个暂停任务并把控制权交还事件循环。

## 使用非阻塞 I/O 与周期轮询

有些同步库提供“非阻塞 I/O”接口。普通的 `something.read()` 可能一直阻塞到有数据可读；非阻塞模式则可能写成：

```python
something.read(block=False)
```

它总是立即返回。如果没有数据，就以某种方式表示，例如返回 `None` 或抛出特定异常。

可以据此快速构造异步读取协程：

```python
async def read_async(data_source):
    while True:
        r = data_source.read(block=False)
        if r is not None:
            return r
        else:
            await asyncio.sleep(0.01)
```

等待这个协程时，它会周期性检查是否有数据：有数据就返回；没有则暂停一小段时间，让事件循环执行其他任务，然后再检查。

这是一种“快速但粗糙”的同步转异步方案，通常不是效率最高的方式，但有时比其他方案简单，而且性能可能已经足够。

使用轮询时应谨慎选择间隔：太短会浪费 CPU，太长会增加响应延迟。还应正确处理取消、超时、异常和资源关闭。

## 监视文件描述符

把同步 I/O 以异步方式使用的最后一种选择，是直接利用操作系统和事件循环提供的底层等待机制。异步库作者通常会采用这种方式。它往往效率最高，但也最难正确实现。

如果底层库能提供“文件描述符（file descriptor）”——操作系统用于标识可等待资源的对象——就可以使用事件循环的 `add_reader` 和 `add_writer`：

- `add_reader(fd, callback, ...)`：文件描述符可读时调用同步回调；
- `add_writer(fd, callback, ...)`：文件描述符可写时调用同步回调。

底层传输机制可能在数据尚不足以完成一次读取，或写入空间仍不足时就触发回调，因此每次回调都必须再次检查实际状态。

改进后的异步读取协程如下：

```python
import asyncio


async def read_async(data_source):
    loop = asyncio.get_running_loop()
    fd = data_source.get_fd()
    fut = loop.create_future()

    def __check_for_read():
        try:
            r = data_source.read(block=False)
        except Exception as e:
            loop.remove_reader(fd)
            fut.set_exception(e)
        else:
            if r is not None:
                loop.remove_reader(fd)
                fut.set_result(r)

    loop.add_reader(fd, __check_for_read)
    return await fut
```

这个版本不再定期睡眠和轮询。它：

1. 创建一个 Future；
2. 向事件循环注册文件描述符可读回调；
3. 等待 Future；
4. 每次回调触发时尝试非阻塞读取；
5. 若读到数据，移除监视器并把 Future 设置为成功结果；
6. 若读取抛出异常，移除监视器并把异常写入 Future；
7. 若暂时仍没有足够数据，则什么也不做，继续等待下次通知。

若能够使用文件描述符，这通常比固定间隔轮询更适合为同步 I/O 提供异步包装。但它不适用于 CPU 密集型工作，也不适用于无法暴露可等待文件描述符的接口。

> **注意：Transport 与 Protocol**  
> `asyncio` 还提供面向网络套接字的 `Transport` 和 `Protocol`。若你正在编写某种网络协议的异步库，或把现有同步协议库改造成异步库，它们会很有用。对于普通应用程序，原文建议除非确有必要，否则优先使用更高层的库。

## 总结

结合本篇和前四篇的内容，你应当已经能够：

- 为大多数应用开发场景编写 `asyncio` 程序；
- 避免在事件循环线程中直接执行阻塞 I/O 或长时间 CPU 计算；
- 使用线程池包装同步阻塞库；
- 对纯 Python CPU 密集型工作使用进程池；
- 在独立同步线程中通过 `run_coroutine_threadsafe` 调用已运行事件循环上的协程；
- 在底层接口允许时，通过非阻塞轮询或文件描述符通知构建更高效的异步包装器。

本系列的目标，是解释作者刚开始使用 `asyncio` 时希望自己已经知道的那些知识，并帮助读者消除对这一部分 Python 的神秘感。

---
