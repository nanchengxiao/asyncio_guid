# Lesson 00 — Python foundation

> 这一课不要求你预先理解 iterator、generator、context manager、lazy 等术语。
> 如果这些词现在看起来陌生，这是正常的；本课会从普通 `for` 循环开始，一个一个解释。

## 本节目标

学完本节，你应该能够：

- 解释 `for` 循环背后的 `iter()` 和 `next()`
- 区分“可以开始遍历的数据”和“记住当前遍历位置的对象”
- 解释 generator 为什么能暂停、以后再从原位置继续
- 解释 `try / finally` 为什么适合做必须发生的收尾
- 解释 `with` 为什么能给资源画出清晰的使用边界
- 最后把这些知识组合成“需要一条时才读取一条，并且退出时一定关闭资源”的小工具

如果上面任何一句现在还说不清，不需要先去别处补课；这正是本节要解决的问题。

## 为什么需要学习它

真正进入 asyncio 之前，我们先建立两个以后会反复使用的直觉：

1. **一段代码可以暂停，稍后从原位置继续。**
2. **一段工作即使提前结束，也必须可靠地做收尾。**

Generator 帮你理解第 1 点；`try/finally` 和 context manager 帮你理解第 2 点。

后面学习 coroutine、cancellation、异步上下文管理器、worker shutdown 时，会不断遇到同样的思想。

本课暂时没有 asyncio 代码。先把同步 Python 的执行过程看清楚，后面会容易很多。

## 先把本课术语翻译成人话

下面这些词会在本课反复出现。第一次看到时，不需要背英文定义，只要先记住“它在代码里做什么”。

| 术语 | 先这样理解 |
|---|---|
| iterable，可迭代对象 | 一份“可以开始遍历”的数据，例如 list、tuple、字符串 |
| iterator，迭代器 | 一次具体遍历过程，自己记得“已经走到哪里” |
| generator，生成器 | 一种会在 `yield` 处暂停、以后还能继续的 iterator |
| resource，资源 | 用完需要关闭、释放或归还的东西，例如文件、连接、锁 |
| cleanup，清理/收尾 | 关闭、释放、归还资源这类必须做的动作 |
| callback，回调函数 | 把一个函数当作参数传进去，稍后再调用它 |
| context manager，上下文管理器 | 用 `with` 表达“进入资源 → 使用 → 退出并清理” |
| lazy，常译“惰性” | **按需处理**：需要一个元素时才产生/读取一个，不提前把全部数据读完 |
| stream，流 | 这里先理解成“可以一条一条取得的数据来源”，不表示某个特殊 Python 类型 |

所以后面如果看到“惰性读取”，请直接在脑中替换成：

> **需要一条时才读取一条，不提前把后面的数据读出来。**

如果看到“记录流”，请替换成：

> **可以逐条取得记录的数据来源。**

## 核心理论

### 1. 从最普通的 `for` 循环开始

```python
numbers = [10, 20, 30]

for number in numbers:
    print(number)
```

通常我们只把它理解成“依次拿出列表里的元素”。

但 Python 实际上要解决两个问题：

- 怎样开始遍历 `numbers`？
- 怎样拿到下一个元素，并记住已经走到哪里？

这两个问题分别对应 iterable 和 iterator。

### 2. iterable：可以开始一次遍历的数据

例如：

```python
numbers = [10, 20, 30]
```

`numbers` 是一个 iterable，因为可以对它调用：

```python
iterator = iter(numbers)
```

先记住这条关系：

```text
可以遍历的数据
    │
    │ iter(...)
    ▼
记住遍历位置的 iterator
```

常见 iterable：

```python
[1, 2, 3]
("a", "b")
"hello"
range(3)
```

### 3. iterator：记住“已经走到哪里”

有了 iterator，就能：

```python
next(iterator)
```

每调用一次，向前走一步：

```python
numbers = [10, 20, 30]
it = iter(numbers)

print(next(it))  # 10
print(next(it))  # 20
print(next(it))  # 30
```

`it` 必须记住自己的位置，否则第二次 `next(it)` 就不知道应该返回 20 还是重新返回 10。

如果再调用：

```python
next(it)
```

会出现：

```text
StopIteration
```

它的意思就是：**没有下一项了，遍历结束。**

同一份 iterable 可以产生多个互不影响的 iterator：

```python
numbers = [10, 20, 30]

a = iter(numbers)
b = iter(numbers)

print(next(a))  # 10
print(next(a))  # 20
print(next(b))  # 10
```

脑内模型：

```text
numbers
├─ iterator a：走到 20
└─ iterator b：走到 10
```

### 4. `for` 循环其实在帮你调用 `iter()` 和 `next()`

这段：

```python
for number in numbers:
    print(number)
```

概念上接近：

```python
it = iter(numbers)

while True:
    try:
        number = next(it)
    except StopIteration:
        break

    print(number)
```

所以 `for` 大致做三件事：

1. 调用 `iter(...)` 得到 iterator；
2. 不断调用 `next(...)`；
3. 遇到 `StopIteration` 时停止。

理解这一点后，generator 就容易很多，因为 generator 本身就是一种 iterator。

### 5. generator function 和 generator object 不是同一个东西

看代码：

```python
def count_two():
    print("A")
    yield 1
    print("B")
    yield 2
    print("C")
```

因为函数体里出现了 `yield`，`count_two` 是一个 generator function（生成器函数）。

现在执行：

```python
g = count_two()
```

此时**不会打印 `A`**。

这次调用只是创建一个 generator object：

```text
count_two       → 生成器函数
count_two()     → 生成器对象
```

函数体还没有真正开始执行。

### 6. 第一次 `next()`：执行到 `yield`，然后暂停

```python
g = count_two()
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
把 1 交给 next(g) 的调用者
    ↓
暂停
```

所以 `value == 1`。

此时函数没有结束，只是停在第一个 `yield` 的位置。

### 7. 第二次 `next()`：从上次暂停处继续

再次：

```python
next(g)
```

执行过程：

```text
从第一个 yield 后恢复
    ↓
print("B")
    ↓
yield 2
    ↓
交出 2
    ↓
再次暂停
```

第三次 `next(g)`：

```text
从第二个 yield 后恢复
    ↓
print("C")
    ↓
函数走到结尾
    ↓
StopIteration
```

完整时间线：

```text
g = count_two()
│
└─ 只创建 generator object，函数体没运行

next(g)
├─ print A
├─ yield 1
└─ 暂停

next(g)
├─ 从上次位置恢复
├─ print B
├─ yield 2
└─ 暂停

next(g)
├─ 从上次位置恢复
├─ print C
└─ StopIteration
```

### 8. 什么是“按需读取（lazy，惰性）”？

现在才正式引入这个术语。

看两个版本。

#### 版本 A：先把全部结果准备好

```python
def make_numbers():
    return [1, 2, 3, 4, 5]
```

调用时，整个 list 已经创建出来。

#### 版本 B：需要一个才产生一个

```python
def make_numbers():
    for number in range(1, 6):
        yield number
```

调用 `make_numbers()` 只得到 generator object。

只有 consumer（使用这些数据的代码）调用 `next()` 时，才真的产生下一项。

这就是本课所说的：

> **按需读取 / 按需产生（lazy，常译为“惰性”）**。

“惰性”不是说程序偷懒，而是说：

```text
需要 1 个 → 只取 1 个
还需要 1 个 → 再取 1 个
不需要了 → 后面的先不取
```

例如：

```python
def source():
    print("produce 1")
    yield 1
    print("produce 2")
    yield 2
    print("produce 3")
    yield 3
```

如果只执行：

```python
g = source()
first = next(g)
```

应该只看到：

```text
produce 1
```

不应该提前出现：

```text
produce 2
produce 3
```

以后测试里如果说“检查按需读取顺序”，具体就是检查这种可观察行为：

> 调一次 `next()`，只推进到下一条数据；没有请求后面的数据时，后面的数据不能提前被生产。

### 9. 什么叫资源？为什么需要 cleanup？

资源不是特殊 Python 类型。

只要“用完后需要关闭、释放或归还”，就可以把它当成资源，例如：

- 文件
- socket
- HTTP connection
- database connection
- lock
- thread pool

例如：

```python
f = open("data.txt")
text = f.read()
f.close()
```

如果中间失败：

```python
f = open("data.txt")
text = risky_read(f)   # 这里抛异常
f.close()              # 这一行不会执行
```

资源可能没有关闭。

### 10. `try / finally`：无论怎样离开，都执行收尾

```python
resource = open_resource()

try:
    use(resource)
finally:
    resource.close()
```

`finally` 的重点不是“处理异常”，而是：

> **离开这个 `try` 控制范围前，必须先执行这里的收尾代码。**

例如：

```python
def demo():
    try:
        print("working")
        return 42
    finally:
        print("cleanup")
```

真正返回 42 前，会先打印 `cleanup`。

同样，在同一个 `try` 范围里因为异常、`return`、`break` 离开时，也会先执行 `finally`。

### 11. 一个容易误解的点：consumer 的 `break` 不等于 generator 一定立刻 cleanup

假设：

```python
def source():
    try:
        yield 1
        yield 2
        yield 3
    finally:
        print("source cleanup")


g = source()

for item in g:
    print(item)
    break
```

`break` 直接表达的只是：

> consumer 不再继续这个 `for` 循环。

不要背成：

> `break` 一发生，generator 的 `finally` 就一定立刻执行。

Generator 是否被显式 `close()`、是否还保留引用等都会影响它自己的关闭时机。

因此，本课 practice **不依赖 consumer 的 `break` 来保证资源关闭**。

我们会使用更明确的生命周期边界：`with`。

### 12. `with`：把资源从进入到退出写成一个代码块

你可能见过：

```python
with open("data.txt") as f:
    text = f.read()
```

先这样理解：

```text
进入 with
   ↓
获得资源 f
   ↓
执行缩进代码块
   ↓
不管正常结束还是抛异常
   ↓
退出时做清理
```

能够支持这种行为的对象叫 context manager（上下文管理器）。

它的目的就是：

> 用代码块明确表达“进入资源 → 使用资源 → 退出并清理”的生命周期。

### 13. context manager 背后的 `__enter__` / `__exit__`

最小例子：

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

脑内顺序：

```text
DemoContext()
    ↓
__enter__()
    ↓
返回 "resource"
    ↓
绑定给 as value
    ↓
执行 with 代码块
    ↓
__exit__()
```

你现在不需要背 `__exit__` 的参数，只要先建立：

```text
enter → use → exit
```

### 14. callback 是什么？

Practice 里的 `close_resource` 是一个 callback。

这不是什么 asyncio 特殊概念，它只是“把函数当作值传进去，稍后调用”。

```python
def close_resource():
    print("closed")


def run_cleanup(callback):
    callback()


run_cleanup(close_resource)
```

测试里还可能看到：

```python
lambda: events.append("closed")
```

这个 lambda 也只是一个小函数：调用时把 `"closed"` 放进 `events`。

### 15. `@contextmanager` 是什么？

手写 `__enter__` / `__exit__` 有时很啰嗦。

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

使用：

```python
with managed_resource() as value:
    print(value)
```

本课不要求你系统学习 decorator（装饰器）。这里只需要知道：

> `@contextmanager` 会把这个 generator function 包装成一个可用于 `with` 的 context manager 工厂。

### 16. `@contextmanager` 里的 `yield` 到底做什么？

```python
@contextmanager
def managed_resource():
    print("before")
    try:
        yield "resource"
    finally:
        print("after")
```

进入 `with` 时：

```text
调用 managed_resource()
    ↓
包装器驱动 generator
    ↓
执行到 yield "resource"
    ↓
暂停
    ↓
"resource" 绑定给 as 后面的变量
```

退出 `with` 时：

```text
恢复 generator
    ↓
继续执行 yield 后面的部分
    ↓
finally cleanup
    ↓
结束
```

可以先记成：

```text
yield 之前  → 进入阶段
yield 的值  → 交给 as 后面的变量
yield 之后  → 退出阶段
finally      → 必须做的收尾
```

### 17. 把所有积木组合起来

业务要求：

> 给我一批 `records`。调用方需要一条时才读取一条，不提前把后面的记录全部读完；但是只要离开 `with`，必须调用 `close_resource()` 一次。

逐条翻译。

#### “需要一条时才读取一条”

不要：

```python
list(records)
```

因为这会立即把所有元素消费完。

而是：

```python
iterator = iter(records)
```

然后把 iterator 交给调用方，让调用方自己决定调用多少次 `next()`。

#### “离开生命周期时一定收尾”

使用：

```text
try
  ├─ 把 iterator 交给 with 代码块
finally
  └─ close_resource()
```

#### “调用方要写成 with ... as records”

使用 `@contextmanager`。

到这里，practice 需要的概念已经全部出现并解释过了。

## 脑内执行模型

假设调用方写：

```python
with managed_records(source(), close_resource) as records:
    first = next(records)
```

脑内时间线：

```text
调用 source()
│
│ 如果 source 是 generator function：
│ 这里只创建 generator object，还没有产生第一个元素
│
调用 managed_records(...)
│
进入 with
│
├─ 得到 iterator
├─ 执行到 @contextmanager 的 yield
└─ 把 iterator 绑定给 as records

with 代码块开始
│
next(records)
│
├─ source 真正向前推进
└─ 只产生第一个元素

with 代码块结束
│
恢复 managed_records
│
└─ finally → close_resource()
```

两个关键结论：

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
  **更准确：** 通常只是创建 generator object；第一次 `next()` 才开始跑。

- **误区：** 每次 `next()` 都从函数第一行重来。  
  **更准确：** 从上一次 `yield` 后继续。

- **误区：** `yield` 等于 `return`。  
  **更准确：** `return` 结束；`yield` 交出值并暂停，以后还能恢复。

- **误区：** “惰性”是某种复杂优化技术。  
  **更准确：** 本课只表示“需要一条才读取一条，不提前读取后面的数据”。

- **误区：** `finally` 是用来捕获异常的。  
  **更准确：** `except` 负责决定是否处理异常；`finally` 负责必须做的收尾。

- **误区：** consumer 一 `break`，generator 一定立即 cleanup。  
  **更准确：** 本课不依赖这个假设，资源关闭由 `with` 生命周期保证。

- **误区：** `@contextmanager` 里的 `yield` 是在不停生成 records。  
  **更准确：** 这里通常只 `yield` 一次，用来分开 context 的进入和退出阶段，并把一个对象交给 `as`。

## 本节规则总结

1. `iter(iterable)` 开始一次遍历，得到 iterator。
2. `next(iterator)` 向前走一步；没有下一项时出现 `StopIteration`。
3. `for` 循环本质上在帮你重复调用 `next()`。
4. Generator function 被调用时，通常只创建 generator object。
5. `yield` 会交出一个值并暂停；下一次从原位置继续。
6. 本课说的 lazy/惰性，就是“按需读取，不提前把后面的数据取出来”。
7. `finally` 适合表达必须发生的收尾。
8. `with` / context manager 给资源建立明确生命周期。
9. `@contextmanager` 用 generator 的一次暂停/恢复表达这个生命周期边界。
10. consumer 是否提前停止，和资源最终由谁负责关闭，是两个不同问题。

## 运行本课实验

仓库提供一个只负责打印执行顺序的实验文件：

```bash
uv run python lessons/00_python_foundation/experiments.py
```

建议先预测，再运行。

至少观察：

1. 创建 generator object 时函数体没有开始打印。
2. 每次 `next()` 只推进到下一个 `yield`。
3. `with` 的进入部分先执行，退出/清理部分最后执行。

## 关键问题

完成 practice 前，尽量先自己回答；答不上时回到对应小节。

1. `[1, 2, 3]` 是 iterable 还是 iterator？
2. `iter([1, 2, 3])` 得到什么？
3. 谁保存“这次遍历已经走到哪里”的状态？
4. `for x in values` 和 `iter()` / `next()` 有什么关系？
5. 为什么调用 generator function 时函数体不会立刻跑完？
6. 第一次执行到 `yield 1` 后，下一次恢复从哪里开始？
7. `return` 和 `yield` 最重要的区别是什么？
8. “按需读取（lazy/惰性）”具体能通过什么行为观察到？
9. 为什么 `list(records)` 会违反“需要一条才读取一条”的要求？
10. `finally` 和 `except` 的职责有什么区别？
11. `with X() as value` 中的 `value` 大致从哪里来？
12. `@contextmanager` 中，`yield` 前、`yield` 的值、`yield` 后分别扮演什么角色？
13. 为什么不能简单形成“consumer `break` ⇒ generator 立即 cleanup”的规则？
14. 本课 practice 中，究竟是什么边界保证 `close_resource()` 被调用？

### 自测 1：generator 什么时候开始执行？

```python
def demo():
    print("A")
    yield 10
    print("B")


g = demo()
print("C")
print(next(g))
```

<details>
<summary>展开答案</summary>

```text
C
A
10
```

`demo()` 只创建 generator object，所以 `A` 不会在创建 `g` 时打印。

</details>

### 自测 2：iterator 走完以后发生什么？

```python
values = [10, 20]
it = iter(values)

print(next(it))
print(next(it))
print(next(it))
```

<details>
<summary>展开答案</summary>

第三次 `next(it)` 会产生 `StopIteration`，表示没有下一项了。

</details>

### 自测 3：什么叫“按需读取顺序”？

```python
events = []

def source():
    for item in [1, 2, 3]:
        events.append(f"produce:{item}")
        yield item


g = source()
first = next(g)
```

此时 `events` 应该是什么？

<details>
<summary>展开答案</summary>

```python
["produce:1"]
```

因为只请求了一个元素，所以只应该生产第一个元素。若已经出现 `produce:2`、`produce:3`，就说明后面的数据被提前读取了。

</details>

### 自测 4：`@contextmanager` 的 `yield` 做什么？

```python
print("before")
yield resource
print("after")
```

<details>
<summary>展开答案</summary>

进入 `with` 时执行到 `yield resource` 并暂停；`resource` 绑定给 `as` 变量。退出 `with` 时恢复，继续执行 `yield` 后面的代码。

</details>

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

1. **按需读取**：进入 `with` 时不能提前把全部 records 读完。
2. `as records` 得到的是 iterator，可以一步一步 `next()`。
3. 离开 `with` 时调用 `close_resource()`。
4. 正常结束、提前停止、异常三条路径都必须执行收尾。
5. 收尾只发生一次。

开始写代码前，请先阅读：

```text
lessons/00_python_foundation/practice/README.md
```

## 验收

参考实现测试：

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
- 正常退出时执行收尾；
- 调用方只读一条后退出 `with` 也执行收尾；
- `with` 代码块抛异常时仍执行收尾；
- `close_resource()` 只调用一次。

测试通过后再看：

```text
lessons/00_python_foundation/solution/reference.py
```

最后逐行解释：

```text
为什么这里要 iter？
为什么这里不能 list？
为什么 yield 只出现一次？
为什么 cleanup 放在 finally？
真正保证资源关闭的生命周期边界是什么？
```
