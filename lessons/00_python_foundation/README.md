# Lesson 00 — Python 必要基础

## 进入本课前

这一课只要求普通 Python 基础：变量、函数、`if` / `for` / `while`、list / dict、模块导入，以及见过 `try / except`。

这一课不会假设你已经理解下面出现的任何新词。

## 本课新增术语

先把本课会用到的词翻译成人话。后面的正文会直接复用这些定义。

- **iterable（可迭代对象）**：一份“可以开始逐项读取”的数据，例如 list、tuple、字符串。
- **iterator（迭代器）**：一次具体的逐项读取过程；它自己记得“已经读到哪里”。
- **`StopIteration`**：告诉调用方“已经没有下一项了”的结束信号。
- **generator（生成器）**：一种可以在 `yield` 处交出一个值并暂停、以后再从原位置继续的 iterator。
- **`yield`**：先把一个值交给调用方，同时把当前执行位置保留下来，下一次再从这里继续。
- **lazy（按需/惰性处理）**：需要一个元素时才产生或读取一个，不提前把后面的全部数据准备好。
- **resource（资源）**：用完需要关闭、释放或归还的东西，例如文件或连接。
- **cleanup（清理/收尾）**：关闭、释放、归还资源这类必须做的动作。
- **`finally`**：离开对应 `try` 范围前一定会执行的收尾代码块。
- **context manager（上下文管理器）**：让 `with` 可以表达“进入资源 → 使用 → 退出并清理”的对象。
- **callback（回调函数）**：把一个函数当作值传进去，等到需要时再调用它。
- **stream（流）**：这里先理解成“可以一条一条取得的数据来源”，不表示某个特殊 Python 类型。
- **`@contextmanager`**：把一个只 `yield` 一次的 generator function 包装成可用于 `with` 的 context manager 的标准库工具。

## 本节目标

学完本节，你应该能够：

- 解释 `for` 循环背后的 `iter()` 与 `next()`；
- 区分 iterable 与 iterator；
- 解释 generator 为什么能暂停并恢复；
- 解释 `yield` 与 `return` 的关键区别；
- 解释 lazy 为什么等价于“需要一个才读取一个”；
- 用 `finally` 和 context manager 保证资源可靠 cleanup；
- 实现一个按需读取、退出时一定关闭资源的小工具。

## 为什么需要学习它

后面的异步课程会反复遇到两个执行问题：

1. 一段工作可以先停在某个位置，之后再从那个位置继续；
2. 一段工作即使提前结束，也必须可靠地做收尾。

这一课先用普通 Python 把这两个行为看清楚。这样后面进入异步代码时，不需要同时学习新语法和新执行模型。

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
it = iter(numbers)

print(next(it))  # 10
print(next(it))  # 20
print(next(it))  # 30
```

`numbers` 是 iterable；`it` 是一次具体的 iterator。

再调用一次：

```python
next(it)
```

会得到 `StopIteration`，表示没有下一项了。

同一份 iterable 可以产生多个互不影响的 iterator：

```python
numbers = [10, 20, 30]

a = iter(numbers)
b = iter(numbers)

print(next(a))  # 10
print(next(a))  # 20
print(next(b))  # 10
```

可以把它想成：

```text
numbers
├─ iterator a：已经走到第二项
└─ iterator b：只走到第一项
```

### 3. `for` 大致帮你做了什么

下面两段代码在概念上接近。

```python
for number in numbers:
    print(number)
```

```python
it = iter(numbers)

while True:
    try:
        number = next(it)
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

函数体里有 `yield`，所以 `count_two` 是一个 generator function。

```python
g = count_two()
```

这一行通常**不会打印 `A`**。它只是创建 generator object。

```text
count_two       → generator function
count_two()     → generator object
```

### 5. `yield`：交出值并暂停

第一次：

```python
value = next(g)
```

执行过程：

```text
进入 count_two
    ↓
print("A")
    ↓
yield 1
    ↓
把 1 交给 next(g)
    ↓
暂停
```

第二次 `next(g)` 会从上次 `yield` 后面继续，而不是从函数第一行重来。

完整时间线：

```text
g = count_two()
└─ 只创建对象，函数体还没运行

next(g)
├─ print A
├─ yield 1
└─ 暂停

next(g)
├─ 从上次位置恢复
├─ print B
├─ yield 2
└─ 再次暂停

next(g)
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


g = source()
first = next(g)
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

### 7. 为什么资源需要 cleanup

资源不是特殊 Python 类型。只要“用完后必须关闭、释放或归还”，就应该明确谁负责 cleanup。

```python
f = open("data.txt")
text = f.read()
f.close()
```

如果中间抛异常：

```python
f = open("data.txt")
text = risky_read(f)  # 这里失败
f.close()             # 这一行不会执行
```

资源就可能没有被关闭。

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


g = source()
for item in g:
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
with open("data.txt") as f:
    text = f.read()
```

脑内顺序：

```text
进入 with
   ↓
获得资源
   ↓
执行缩进代码块
   ↓
无论正常结束还是抛异常
   ↓
退出并做 cleanup
```

最小的 context manager 可以写成：

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

你不需要背 `__exit__` 的参数，只要先记住：

```text
enter → use → exit
```

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

什么时候确定执行资源关闭？
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
  **更准确：** 本课不依赖这个假设，资源关闭由 `with` 的生命周期保证。

## 本节规则总结

1. `iter(iterable)` 开始一次遍历，得到 iterator。
2. `next(iterator)` 向前走一步；没有下一项时出现 `StopIteration`。
3. `for` 循环大致在帮你重复调用 `next()`。
4. generator function 被调用时，通常只创建 generator object。
5. `yield` 交出一个值并暂停；下一次从原位置继续。
6. lazy 就是按需读取，不提前把后面的内容取出来。
7. `finally` 适合表达必须发生的收尾。
8. `with` / context manager 给资源建立明确的使用边界。
9. `@contextmanager` 用一次 `yield` 把进入阶段和退出阶段分开。
10. 调用方是否提前停止，与资源最终由谁负责关闭，是两个不同问题。

## 关键问题

1. `[1, 2, 3]` 是 iterable 还是 iterator？
2. `iter([1, 2, 3])` 得到什么？
3. 谁保存“这次遍历已经走到哪里”的状态？
4. `for x in values` 与 `iter()` / `next()` 有什么关系？
5. 为什么调用 generator function 时函数体不会立刻跑完？
6. 第一次执行到 `yield 1` 后，下一次从哪里恢复？
7. `return` 与 `yield` 最重要的区别是什么？
8. lazy 行为可以通过什么具体输出观察？
9. 为什么 `list(records)` 会违反按需读取？
10. `finally` 与 `except` 的职责有什么区别？
11. `with X() as value` 中的 `value` 大致从哪里来？
12. `@contextmanager` 中，`yield` 前、`yield` 的值、`yield` 后分别做什么？
13. 为什么不能形成“`break` ⇒ generator 立即 cleanup”的规则？
14. 本课 practice 中，是什么边界保证 `close_resource()` 被调用？

## 场景命题

实现 `managed_records(records, close_resource)`。

业务场景：报表导入器从一个需要显式关闭的数据源逐条读取记录。调用方可能：

- 读取全部数据；
- 只读取第一条就停止；
- 在处理过程中抛异常。

无论哪条路径，只要离开 `with`，资源都必须关闭一次。

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

开始写代码前，请阅读：

```text
lessons/00_python_foundation/practice/README.md
```

## 验收

先运行本课实验，观察执行顺序：

```bash
uv run python lessons/00_python_foundation/experiments.py
```

仓库参考实现：

```bash
uv run pytest lessons/00_python_foundation/tests -v
```

完成自己的 starter 后：

```bash
uv run pytest lessons/00_python_foundation/tests -v --learner
```

测试观察的是具体行为：

- 进入 `with` 时不能提前读取数据；
- 调一次 `next()` 只读取下一条；
- 正常退出时执行 cleanup；
- 调用方只读一条后退出 `with` 也执行 cleanup；
- `with` 代码块抛异常时仍执行 cleanup；
- `close_resource()` 只调用一次。
