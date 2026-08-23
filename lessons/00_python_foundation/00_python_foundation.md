# Lesson 00 — Python 必要基础

## 进入本课前

这一课只要求普通 Python 基础：变量、函数、`if` / `for` / `while`、list / dict、模块导入，以及见过 `try / except`。

这一课不会假设你已经理解下面出现的任何新词。

本课信息量较大，建议分两遍学习。第一遍只抓住一条主线：数据按需产生，调用方只读取一条就离开，关闭动作仍然可靠执行。先运行 `case.py` 并能复述这条时间线，再回到“核心理论”补齐每一种对象和语法的名字。已经熟悉本课内容的学习者，可以运行示例、回答“关键问题”后直接进入 Lesson 01。

## 本课新增术语

本课要补齐三组普通 Python 积木。词看起来不少，不需要现在背诵；先知道它们分别位于“逐项读取”“暂停后继续”“resource 收尾”哪一层，紧接着再全部对到同一个例子上。

**第一组：逐项读取**

- **iterable（可迭代对象）**：一份“可以开始逐项读取”的数据，例如 list、tuple、字符串。
- **iterator（迭代器）**：一次具体的逐项读取过程；它自己记得“已经读到哪里”。
- **`iter(...)`**：根据一个 iterable 创建一次 iterator。
- **`next(...)`**：向 iterator 请求下一项，并让它把当前位置向前推进一步。
- **`StopIteration`**：iterator 已经没有下一项时，用来告诉调用方“遍历结束了”的信号。

**第二组：暂停后继续与按需读取**

- **`yield`**：先把一个值交给调用方，同时把当前执行位置保留下来，下一次再从这里继续。
- **generator（生成器）**：一种可以在 `yield` 处交出一个值并暂停、以后再从原位置继续的 iterator。
- **generator function（生成器函数）**：函数体中使用了 `yield` 的函数；调用它时通常不会立刻跑完整个函数体。
- **generator object（生成器对象）**：调用 generator function 后得到的 iterator；它保存暂停位置，之后可以继续。
- **lazy（按需/惰性处理）**：需要一个元素时才产生或读取一个，不提前把后面的全部数据准备好。

**第三组：resource 使用边界与收尾**

- **resource（资源）**：用完后需要明确关闭、释放或归还的东西，例如打开的文件或数据源。
- **cleanup（清理/收尾）**：关闭、释放、归还 resource 这类必须做的动作。
- **`finally`**：离开对应 `try` 范围前一定会执行的收尾代码块。
- **`with`**：用一个缩进代码块明确表示“进入某个使用范围，结束时再退出这个范围”的 Python 语法。
- **context manager（上下文管理器）**：让 `with` 能够执行“进入 → 使用 → 退出并 cleanup”这套流程的对象。
- **`__enter__()`**：进入 `with` 时由 Python 调用的方法；它可以准备并交出要使用的对象。
- **`__exit__()`**：离开 `with` 时由 Python 调用的方法；它可以执行 cleanup。
- **callback（回调函数）**：把一个函数当作值传进去，等到需要时再调用它。
- **stream（流）**：这里先理解成“可以一条一条取得的数据来源”，不表示某个特殊 Python 类型。
- **`@contextmanager`**：把一个只 `yield` 一次的 generator function 包装成可用于 `with` 的 context manager 的标准库工具。

## 一个例子串起全部术语

上面的词很多，但它们可以落在同一件事上：调用方只读取一条记录就提前离开，数据源仍然必须可靠收尾。下面这段代码就是本课的 `case.py`：

```python
from contextlib import contextmanager

def source():
    """generator function：按需产生数据，请求一条才读取一条。"""
    for number in (1, 2, 3):
        print(f"produce {number}")
        yield number

def close_resource():
    """resource 的收尾动作，稍后作为 callback 传给 context manager。"""
    print("closed：resource 收尾")

@contextmanager
def managed_records(records, cleanup_callback):
    try:
        yield iter(records)      # yield 前：进入阶段；yield 后：退出阶段
    finally:
        cleanup_callback()       # 无论正常结束还是抛异常，离开 with 都会收尾

def main():
    records_generator = source()
    # 调用 source() 只是创建 generator object，函数体还没有运行
    with managed_records(records_generator, close_resource) as records:
        first = next(records)    # lazy：需要 1 条，只读取 1 条
        print(f"got {first}")
        # 不要在这里 list(records)：那会立即把剩余内容全部读完
    # 离开 with 后，close_resource() 已经执行

main()
```

真实输出：

```text
produce 1
got 1
closed：resource 收尾
```

把本课知识点对到代码上：

| 术语或知识点 | 在这个例子里指什么 |
| --- | --- |
| **iterable** | `source()` 内部的 `(1, 2, 3)` 可以开始逐项读取 |
| **iterator** | `records_generator` 是一次具体读取过程；`records` 指向由 `iter(records)` 得到的 iterator |
| **`iter(...)`** | `yield iter(records)` 取得本次读取使用的 iterator；generator object 本身已经是 iterator，所以这里仍得到它自己 |
| **`next(...)`** | `next(records)` 只请求下一项，并把读取位置推进一步 |
| **`StopIteration`** | 本例只读取第一项，没有走到结束；如果继续请求到第三项之后，它会用这个信号表示没有下一项 |
| **`yield`** | `source()` 中交出一条数据并保存读取位置；`managed_records()` 中分隔进入与退出阶段 |
| **generator** | `source()` 创建的逐项读取过程，能够在每次 `yield` 后暂停并继续 |
| **generator function** | `source` 直接是 generator function；`managed_records` 的原始函数体也使用 `yield`，随后由 `@contextmanager` 包装 |
| **generator object** | `records_generator = source()` 得到的对象；创建时 `produce 1` 还没有执行 |
| **lazy** | 代码只调用一次 `next(records)`，所以只出现 `produce 1`，不会提前产生 2 和 3 |
| **resource** | 例子用数据源代表一项需要在使用结束后关闭的东西 |
| **cleanup** | `close_resource()` 打印 `closed`，代表真正的关闭或释放动作 |
| **`finally`** | 保证控制流离开 `with` 时一定调用 `close_resource()` |
| **`with`** | `with managed_records(...)` 明确数据源的使用范围 |
| **context manager** | `managed_records(...)` 返回的对象负责进入、交出 `records`，以及退出时收尾 |
| **`__enter__()` / `__exit__()`** | 由 `@contextmanager` 生成的对象提供，`with` 在进入和退出时隐式调用；业务代码不需要手写 |
| **callback** | `close_resource` 作为函数值传入并绑定到 `cleanup_callback`，到退出阶段才被调用 |
| **stream** | `source()` 表示可以一条一条取得的数据来源 |
| **`@contextmanager`** | 把 `managed_records()` 这个只交出一次值的 generator function 包装成 context manager |

按时间线读输出：

1. `main()` 调用 `source()`，只创建 generator object，`source()` 函数体还没有执行。
2. 进入 `with` 时，`managed_records()` 运行到自己的 `yield`，把 iterator 绑定给 `records`。
3. `next(records)` 第一次推进 `source()`，所以先打印 `produce 1`。
4. `source()` 在 `yield number` 暂停并交出 `1`，随后打印 `got 1`。
5. 代码没有再次调用 `next()`，所以 2 和 3 都没有被提前产生。
6. 离开 `with` 时，`managed_records()` 从自己的 `yield` 后恢复并进入 `finally`。
7. `finally` 调用 callback，于是打印 `closed：resource 收尾`；即使只读取一项，cleanup 也没有丢失。

## 本节目标

学完本节，你应该能够：

- 解释 `for` 循环背后的 `iter()` 与 `next()`；
- 区分 iterable 与 iterator；
- 解释 generator 为什么能暂停并恢复；
- 解释 `yield` 与 `return` 的关键区别；
- 解释 lazy 为什么等价于“需要一个才读取一个”；
- 用 `finally` 和 context manager 保证 resource 可靠 cleanup；
- 实现一个按需读取、退出时一定关闭 resource 的小工具。

## 为什么需要学习它

后面的课程会反复遇到两个执行问题：

1. 一段工作可以先停在某个位置，之后再从那个位置继续；
2. 一段工作即使提前结束，也必须可靠地做收尾。

这一课先用普通 Python 把这两个行为看清楚。这样后面学习新的执行方式时，不需要同时猜新语法和新执行模型。

## 核心理论

### 1. 从普通 `for` 循环开始

```python
numbers = [10, 20, 30]

for number in numbers:
    print(number)
```

`for` 看起来只是“依次拿元素”，但 Python 实际上需要回答两个问题：

- 怎样开始这次遍历？
- 怎样拿到下一项，并记住已经走到哪里？

第一件事由 `iter(...)` 完成，第二件事由 iterator 的 `next(...)` 完成。

### 2. iterable 与 iterator

```python
numbers = [10, 20, 30]
number_iterator = iter(numbers)

print(next(number_iterator))  # 10
print(next(number_iterator))  # 20
print(next(number_iterator))  # 30
```

`numbers` 是 iterable；`number_iterator` 是一次具体的 iterator。

再调用一次：

```python
next(number_iterator)
```

会得到 `StopIteration`，表示没有下一项了。

同一份 iterable 可以产生多个互不影响的 iterator：

```python
numbers = [10, 20, 30]

first_iterator = iter(numbers)
second_iterator = iter(numbers)

print(next(first_iterator))   # 10
print(next(first_iterator))   # 20
print(next(second_iterator))  # 10
```

可以把它想成：

```text
numbers
├─ first_iterator：已经走到第二项
└─ second_iterator：只走到第一项
```

### 3. `for` 大致帮你做了什么

下面两段代码在概念上接近。

```python
for number in numbers:
    print(number)
```

```python
number_iterator = iter(numbers)

while True:
    try:
        number = next(number_iterator)
    except StopIteration:
        break

    print(number)
```

所以 `for` 大致在帮你：

1. 调用 `iter(...)`；
2. 反复调用 `next(...)`；
3. 遇到 `StopIteration` 时停止。

### 4. generator function 与 generator object

看这段代码：

```python
def count_two():
    print("A")
    yield 1
    print("B")
    yield 2
    print("C")
```

函数体里有 `yield`，所以 `count_two` 是 generator function。

```python
counter_generator = count_two()
```

这一行通常**不会打印 `A`**。它只是创建 generator object。

```text
count_two       → generator function
count_two()     → generator object
```

### 5. `yield`：交出值并暂停

第一次：

```python
value = next(counter_generator)
```

执行过程：

```text
进入 count_two
    ↓
print("A")
    ↓
yield 1
    ↓
把 1 交给 next(counter_generator)
    ↓
暂停
```

第二次 `next(counter_generator)` 会从上次 `yield` 后面继续，而不是从函数第一行重来。

完整时间线：

```text
counter_generator = count_two()
└─ 只创建对象，函数体还没运行

next(counter_generator)
├─ print A
├─ yield 1
└─ 暂停

next(counter_generator)
├─ 从上次位置恢复
├─ print B
├─ yield 2
└─ 再次暂停

next(counter_generator)
├─ 从上次位置恢复
├─ print C
└─ StopIteration
```

`return` 与 `yield` 最重要的区别是：

```text
return → 结束这次函数执行
yield  → 交出一个值并暂停，之后还能继续
```

### 6. lazy：需要一个才产生一个

先看一次性准备全部结果：

```python
def make_numbers():
    return [1, 2, 3, 4, 5]
```

再看按需产生：

```python
def make_numbers():
    for number in range(1, 6):
        yield number
```

第二个版本只有在调用方真正请求下一项时，才继续向前执行。

```python
def source():
    print("produce 1")
    yield 1
    print("produce 2")
    yield 2
    print("produce 3")
    yield 3


records_generator = source()
first = next(records_generator)
```

此时只应该看到：

```text
produce 1
```

没有请求第二项，就不应该提前出现 `produce 2`。

这就是本课说的 lazy：

```text
需要 1 个 → 只取 1 个
还需要 1 个 → 再取 1 个
不需要了 → 后面的先不取
```

### 7. 为什么 resource 需要 cleanup

Resource 不是特殊 Python 类型。只要“用完后必须关闭、释放或归还”，就应该明确谁负责 cleanup。

```python
file = open("data.txt")
text = file.read()
file.close()
```

如果中间抛异常：

```python
file = open("data.txt")
text = risky_read(file)  # 这里失败
file.close()             # 这一行不会执行
```

Resource 就可能没有被关闭。

### 8. `finally`：离开前一定做收尾

```python
resource = open_resource()

try:
    use(resource)
finally:
    resource.close()
```

重点不是“捕获异常”，而是：

> 离开这个 `try` 范围前，先执行 `finally` 里的收尾。

例如：

```python
def demo():
    try:
        return 42
    finally:
        print("cleanup")
```

真正返回 42 前会先打印 `cleanup`。

### 9. `break` 不等于 generator 一定立即 cleanup

```python
def source():
    try:
        yield 1
        yield 2
    finally:
        print("source cleanup")


records_generator = source()
for item in records_generator:
    print(item)
    break
```

`break` 直接表达的只是：调用方不再继续这个 `for` 循环。

不要把它背成：

> `break` 一发生，generator 的 `finally` 就一定立刻执行。

Generator 何时被显式关闭、是否还保留引用，都会影响它自己的关闭时机。

因此本课 practice 不依赖 `break` 保证 cleanup，而是使用更明确的 `with` 边界。

### 10. `with` 与 context manager

你可能见过：

```python
with open("data.txt") as file:
    text = file.read()
```

脑内顺序：

```text
进入 with
   ↓
获得 resource
   ↓
执行缩进代码块
   ↓
无论正常结束还是抛异常
   ↓
退出并做 cleanup
```

最小的 context manager 可以写成：

下面的 `class` 语法只是把 `__enter__()` 与 `__exit__()` 两个相关方法放到同一种对象上，方便看清 Python 何时调用它们；本课练习使用更短的 `@contextmanager`，不要求你先学会手写这个 class。

```python
class DemoContext:
    def __enter__(self):
        print("enter")
        return "resource"

    def __exit__(self, exc_type, exc, tb):
        print("exit")


with DemoContext() as value:
    print(value)
```

现在可以把执行顺序直接对应到术语表：进入 `with` 时调用 `__enter__()`，离开时调用 `__exit__()`。

### 11. callback

Practice 里的 `close_resource` 是一个 callback。

```python
def close_resource():
    print("closed")


def run_cleanup(callback):
    callback()


run_cleanup(close_resource)
```

这里没有特殊机制，只是把函数当作值传进去，稍后再调用。

### 12. `@contextmanager`

标准库提供：

```python
from contextlib import contextmanager
```

可以这样写：

```python
@contextmanager
def managed_resource():
    print("enter")
    try:
        yield "resource"
    finally:
        print("exit")
```

使用方式：

```python
with managed_resource() as value:
    print(value)
```

这里的 `yield` 只出现一次，用来分开进入阶段和退出阶段：

```text
yield 之前 → 进入阶段
yield 的值 → 交给 as 后面的变量
yield 之后 → 退出阶段
finally     → 必须做的收尾
```

### 13. 把所有积木组合起来

本课 practice 要实现：

```python
with managed_records(source(), close_resource) as records:
    first = next(records)
```

业务要求只有两个：

1. 调用方需要一条时才读取一条；
2. 只要离开 `with`，就调用 `close_resource()` 一次。

第一点由 iterator 的按需推进保证；第二点由 context manager + `finally` 保证。

不要写：

```python
list(records)
```

因为它会立即把剩余内容全部读完，破坏 lazy 行为。

## 脑内执行模型

假设：

```python
with managed_records(source(), close_resource) as records:
    first = next(records)
```

时间线：

```text
调用 source()
└─ 如果它是 generator function，只创建 generator object

调用 managed_records(...)
└─ 进入 with
   ├─ 得到 iterator
   ├─ 执行到 @contextmanager 的 yield
   └─ 把 iterator 绑定给 records

执行 next(records)
└─ source 只向前推进到下一项

离开 with
└─ 恢复 managed_records
   └─ finally → close_resource()
```

两个关键问题：

```text
什么时候读取下一条？
→ 调用方真正调用 next() 时

什么时候确定执行 resource 关闭？
→ 退出 with 时
```

## 常见误解

- **误区：** iterable 和 iterator 是同一个东西。  
  **更准确：** iterable 是“可以开始遍历的数据”；iterator 是“一次具体遍历，记住当前位置”。

- **误区：** 调用 generator function 会立刻执行函数体。  
  **更准确：** 通常只是创建 generator object；第一次 `next()` 才开始推进。

- **误区：** 每次 `next()` 都从函数第一行重来。  
  **更准确：** 从上一次 `yield` 后继续。

- **误区：** `yield` 等于 `return`。  
  **更准确：** `return` 结束；`yield` 交出值并暂停。

- **误区：** lazy 是某种复杂优化。  
  **更准确：** 本课只表示“需要一个才读取一个，不提前读取后面的内容”。

- **误区：** `finally` 用来处理异常。  
  **更准确：** `except` 决定是否处理异常；`finally` 负责必须做的收尾。

- **误区：** 调用方一 `break`，generator 一定立即 cleanup。  
  **更准确：** 本课不依赖这个假设，resource 关闭由 `with` 的进入/退出边界保证。

## 本节规则总结

1. `iter(iterable)` 开始一次遍历，得到 iterator。
2. `next(iterator)` 向前走一步；没有下一项时出现 `StopIteration`。
3. `for` 循环大致在帮你重复调用 `next()`。
4. generator function 被调用时，通常只创建 generator object。
5. `yield` 交出一个值并暂停；下一次从原位置继续。
6. lazy 就是按需读取，不提前把后面的内容取出来。
7. `finally` 适合表达必须发生的收尾。
8. `with` / context manager 给 resource 建立明确的使用边界。
9. `@contextmanager` 用一次 `yield` 把进入阶段和退出阶段分开。
10. 调用方是否提前停止，与 resource 最终由谁负责关闭，是两个不同问题。

## 关键问题

1. `[1, 2, 3]` 是 iterable 还是 iterator？
2. `iter([1, 2, 3])` 得到什么？
3. `next(iterator)` 做什么？
4. 谁保存“这次遍历已经走到哪里”的状态？
5. `for item in values` 与 `iter()` / `next()` 有什么关系？
6. generator function 与 generator object 有什么区别？
7. 为什么调用 generator function 时函数体不会立刻跑完？
8. 第一次执行到 `yield 1` 后，下一次从哪里恢复？
9. `return` 与 `yield` 最重要的区别是什么？
10. lazy 行为可以通过什么具体输出观察？
11. 为什么 `list(records)` 会违反按需读取？
12. `finally` 与 `except` 的职责有什么区别？
13. `with X() as value` 中的 `value` 大致从哪里来？
14. `__enter__()` 与 `__exit__()` 分别在什么时候调用？
15. `@contextmanager` 中，`yield` 前、`yield` 的值、`yield` 后分别做什么？
16. 为什么不能形成“`break` ⇒ generator 立即 cleanup”的规则？
17. 本课 practice 中，是什么边界保证 `close_resource()` 被调用？

## 场景命题

实现 `managed_records(records, close_resource)`。

业务场景：报表导入器从一个需要显式关闭的数据源逐条读取记录。调用方可能：

- 读取全部数据；
- 只读取第一条就停止；
- 在处理过程中抛异常。

无论哪条路径，只要离开 `with`，resource 都必须关闭一次。

调用方式：

```python
with managed_records(source(), close_resource) as records:
    first = next(records)
```

要求：

1. 进入 `with` 时不能提前把全部 records 读完；
2. `as records` 得到 iterator，可以一步一步 `next()`；
3. 离开 `with` 时调用 `close_resource()`；
4. 正常结束、提前停止、异常三条路径都必须 cleanup；
5. cleanup 只发生一次。

练习也可以分两步完成：先让 `source()` 与 `next()` 表现出按需读取，再加入 `managed_records()`，分别检查正常结束、提前停止与异常路径的 cleanup。

---

完成本课后：继续 [Lesson 01 — 函数被调用后，代码什么时候真正开始执行](../01_coroutine_and_await/01_coroutine_and_await.md)。
