# 《图解设计模式》23 种设计模式：Python 快速学习版

> 适合读者：刚读完 / 正在读《好代码，坏代码》，准备进入设计模式学习的人。
> 目标：不是背 23 个模式，而是学会识别 **“哪里在变化、哪里耦合过高、哪里认知负担太大”**，然后用合适的设计模式改善代码。

---

## 0. 先建立一个正确的学习视角

从《好代码，坏代码》进入设计模式时，最重要的一点是：

> **设计模式不是为了“套模式”，而是为了更安全地管理变化。**

你可以把它和《好代码，坏代码》里的思想这样对应：

| 《好代码，坏代码》中的关注点 | 设计模式中的对应思路                         |
| ---------------------------- | -------------------------------------------- |
| 降低耦合                     | Strategy、Observer、Mediator、Facade         |
| 隐藏实现细节                 | Facade、Proxy、Adapter                       |
| 面向抽象而不是具体实现       | Factory Method、Abstract Factory、Strategy   |
| 避免大型`if / elif`        | Strategy、State、Chain of Responsibility     |
| 让修改集中在局部             | Decorator、Command、Visitor                  |
| 提高可测试性                 | Strategy、Factory、Dependency Injection 思维 |
| 降低认知负担                 | Facade、Composite、Builder、Template Method  |

学习每个模式时，优先问 4 个问题：

1. **原始代码的问题是什么？**
2. **什么东西会变化？**
3. **模式把变化隔离到了哪里？**
4. **它带来了什么额外复杂度？**

### 示例代码的原则：先典型，再简洁

这份教程里的示例代码优先满足一个要求：

> **代码里要真的出现这个模式想解决的痛点。**

然后才在不破坏典型性的前提下尽量缩短。

如果一个模式说自己在解决“十几个构造参数”，示例却只有两个字段；或者说在解决“两条独立变化轴”，示例却只有一边在变化，那么代码即使很短，也只是在展示模式的形状，不算好的教学示例。

### 新手先记住 5 个高频词

后面第一次遇到更陌生的术语时，也会尽量用一句话先解释。这里先把最常见的 5 个词说清楚：

- **耦合**：两段代码互相知道得越多、改一边越容易牵动另一边，耦合就越高。
- **抽象**：先规定“能做什么”，把“具体怎么做”藏在后面。
- **接口**：别人应该用哪些方法和参数来调用一个对象。
- **组合**：一个对象内部持有并使用另一个对象，而不是一定靠继承获得能力。
- **依赖注入**：对象需要的工具由外部传进来，而不是在自己内部写死并创建。

不用急着背定义。后面看到具体代码时，再把这些词和代码对应起来即可。

---

# 一、创建型模式

创建型模式关注：

> **对象应该怎样被创建？**

共 5 个：

- Factory Method
- Abstract Factory
- Builder
- Prototype
- Singleton

---

## 1. Factory Method —— 工厂方法

### 解决什么问题

调用者不应该依赖具体类的创建过程。

如果业务代码里到处写：

```python
product = IDCard()
```

那么调用方就和 `IDCard` 强耦合。

Factory Method 把：

> **“创建什么对象”**

交给子类决定。

先直觉理解两个词：

- **具体类**：就是你能直接 `IDCard()` 创建出来的那个实际类。
- **耦合**：一段代码越依赖另一个具体实现，就越难在不改它的情况下替换实现。

真正的问题不是 `IDCard()` 这行代码本身，而是它如果散落在很多业务代码里，未来换一种卡片时，很多地方都要跟着改。

例如，不用 Factory Method 时可能会写成：

```python
def register_user(card_type):
    if card_type == "id":
        card = IDCard()
    elif card_type == "employee":
        card = EmployeeCard()

    card.use()
```

随着卡片类型增加，`register_user()` 会越来越清楚“有哪些卡、怎么创建卡”。Factory Method 想做的是把这部分创建知识移出去，让业务流程只关心“拿到一个可用的 Product”。

### Python 典型示例

```python
from abc import ABC, abstractmethod


class Product(ABC):
    @abstractmethod
    def use(self):
        pass


class IDCard(Product):
    def use(self):
        print("使用身份证")


class EmployeeCard(Product):
    def use(self):
        print("使用员工卡")


class Factory(ABC):
    def create(self):
        product = self.create_product()
        print("登记创建记录")
        return product

    @abstractmethod
    def create_product(self):
        pass


class IDCardFactory(Factory):
    def create_product(self):
        return IDCard()


class EmployeeCardFactory(Factory):
    def create_product(self):
        return EmployeeCard()


def issue_card(factory):
    card = factory.create()
    card.use()


issue_card(IDCardFactory())
issue_card(EmployeeCardFactory())
```

### 怎么理解

`Factory.create()` 定义创建流程：

```text
Factory.create()
      ↓
create_product()
      ↓
具体产品
```

父类知道：

> 我要创建一个 Product。

但不知道：

> 到底是 IDCard、Car 还是 Button。

先看代码里的两个新东西：`ABC` 是 Python 的“抽象基类”工具，`@abstractmethod` 表示“这个方法只规定名字和要求，具体子类必须自己实现”。

可以把 Factory Method 想成“**父类规定开店流程，子类决定店里具体卖什么**”。

`Factory.create()` 是相对稳定的流程；`create_product()` 是留出来的变化点。这里的 **变化点** 就是“未来最可能需要替换或扩展的那一小块代码”。

因此你看这个模式时，不要只记“多写一个工厂类”，而要看依赖方向发生了什么变化：

```text
原来：业务代码 → IDCard
现在：业务代码 → Product / Factory
                    ↓
                 IDCard
```

业务代码不再必须知道具体产品是谁，具体创建细节被推到了更靠近实现的一侧。

### 与《好代码，坏代码》的连接

核心是：

> **依赖抽象，而不是依赖具体实现。**

如果未来增加：

```text
IDCard
Passport
EmployeeCard
```

调用者不需要理解每个具体类的初始化细节。

### 常见场景

- **通知发送器**：业务流程只调用 `sender.send()`，由工厂创建 `EmailSender`、`SMSSender` 或 `PushSender`。
- **文件导入器**：根据文件类型创建 `CSVParser`、`JSONParser`，导入流程不直接依赖具体解析器。
- **存储实现切换**：测试环境创建本地文件存储，线上环境创建云存储客户端。

### 常见误用

不要为了创建一个简单对象就专门写工厂：

```python
User(name)
```

已经很清楚时，没有必要变成：

```python
UserFactory.create_user(name)
```

除了“简单对象没必要加工厂”之外，还常见两种误用：

- **只是把 `IDCard()` 搬进 `IDCardFactory.create()`，但业务仍到处依赖 `IDCardFactory`**：这样只是多绕一层，并没有真正隔离变化。
- **为了猜测未来可能出现的几十种产品提前设计复杂工厂层次**：如果变化还不存在，先保持直接构造通常更容易理解。

判断标准很简单：只有“创建规则本身正在变复杂，或业务不应该知道具体类”时，工厂才真正有价值。

---

## 2. Abstract Factory —— 抽象工厂

### 解决什么问题

Factory Method 常用于创建一个产品。

Abstract Factory 用来创建：

> **一整组相互关联的产品。**

例如：

```text
WindowsButton
WindowsCheckbox

MacButton
MacCheckbox
```

你希望 Windows 风格组件总是配套出现。

这里的 **产品族** 可以简单理解为：**应该成套出现的一组对象**。

问题通常不是“某个对象难创建”，而是你必须保证一整套对象不要混搭。例如 Windows 按钮应该搭配 Windows 复选框，而不是误配成 Mac 复选框。

不用 Abstract Factory 时，调用方可能会自己判断：

```python
if platform == "windows":
    button = WindowsButton()
    checkbox = WindowsCheckbox()
else:
    button = MacButton()
    checkbox = MacCheckbox()
```

如果以后再增加菜单、输入框、弹窗，这个判断会不断变长，而且每个调用方都可能写出不同的组合。Abstract Factory 把“这一套应该怎么配”集中到一个工厂中。

### Python 典型示例

```python
class WindowsButton:
    def render(self):
        print("Windows Button")


class WindowsCheckbox:
    def render(self):
        print("Windows Checkbox")


class MacButton:
    def render(self):
        print("Mac Button")


class MacCheckbox:
    def render(self):
        print("Mac Checkbox")


class WindowsFactory:
    def create_button(self):
        return WindowsButton()

    def create_checkbox(self):
        return WindowsCheckbox()


class MacFactory:
    def create_button(self):
        return MacButton()

    def create_checkbox(self):
        return MacCheckbox()


def build_ui(factory):
    button = factory.create_button()
    checkbox = factory.create_checkbox()

    button.render()
    checkbox.render()


build_ui(MacFactory())
```

### 怎么理解

```text
              UI Factory
              /       \
        Windows       Mac
        /    \       /   \
    Button Checkbox Button Checkbox
```

调用代码只认识：

```python
factory.create_button()
factory.create_checkbox()
```

不关心具体平台。

可以把 Abstract Factory 想成“**选装修套餐**”。

你不是分别挑一个按钮、一个复选框，而是先选：

```text
Windows 套餐
或
Mac 套餐
```

选定工厂后，它生产出来的对象天然属于同一套风格。

这个模式真正保护的是“组合一致性”。调用者不再负责记住哪些对象应该搭配，而是把这个规则交给工厂。

### 与《好代码，坏代码》的连接

它降低了：

> **业务逻辑对具体实现族的依赖。**

尤其适合：

- 多数据库实现
- 多云厂商
- 多 UI 平台
- 多支付渠道

### 常见场景

- **多数据库支持**：MySQL 工厂成套创建 `MySQLConnection + MySQLQueryBuilder`，PostgreSQL 工厂创建对应的一整套对象。
- **跨平台 GUI**：Windows 工厂创建 Windows 风格的按钮、复选框、输入框；Mac 工厂创建 Mac 风格的一套组件。
- **多云部署**：选择某个云厂商后，成套创建它的对象存储、消息队列和监控客户端，避免混用。

### 常见误用

如果产品之间没有“必须成套”的关系，就不要使用 Abstract Factory。

另外要避免两个方向：

- 只有一个 `Button`，却为了“以后可能跨平台”先造完整 Abstract Factory，通常属于过早抽象。
- 产品已经不需要成套变化，却硬塞进同一个工厂，会让工厂承担没有必要的职责。

最适合它的信号是：**你经常需要整体切换一套实现，而且不希望不同套件被混用。**

---

## 3. Builder —— 建造者

### 解决什么问题

当一个对象创建过程很复杂时：

```python
Computer(cpu, memory, storage, gpu, os, wifi, bluetooth, ...)
```

参数越来越多，可读性会迅速下降。

Builder 把复杂对象的创建：

> **拆成多个清楚的小步骤。**

这里的 **构造** 就是“把一个对象需要的数据准备好并创建出来”。

Builder 主要解决的不是“参数多”三个字，而是：**创建一个对象时需要记住太多参数、顺序和可选组合**。

例如：

```python
computer = Computer(
    "Intel",
    "32GB",
    "1TB",
    None,
    "Windows",
    True,
    False,
)
```

只看调用代码，你很难立刻知道 `None`、`True`、`False` 分别代表什么。参数再多一些，调用者就很容易传错位置。

Builder 把一次难读的创建过程拆成有名字的步骤，让代码自己说明“正在配置什么”。

### Python 典型示例

```python
class Computer:
    def __init__(
        self,
        cpu,
        memory,
        storage,
        gpu,
        os,
        wifi,
        bluetooth,
    ):
        self.cpu = cpu
        self.memory = memory
        self.storage = storage
        self.gpu = gpu
        self.os = os
        self.wifi = wifi
        self.bluetooth = bluetooth

    def __str__(self):
        return (
            f"CPU={self.cpu}, Memory={self.memory}, "
            f"Storage={self.storage}, GPU={self.gpu}, OS={self.os}"
        )


class ComputerBuilder:
    def __init__(self):
        self._cpu = None
        self._memory = None
        self._storage = None
        self._gpu = None
        self._os = "Linux"
        self._wifi = True
        self._bluetooth = False

    def with_cpu(self, value):
        self._cpu = value
        return self

    def with_memory(self, value):
        self._memory = value
        return self

    def with_storage(self, value):
        self._storage = value
        return self

    def with_gpu(self, value):
        self._gpu = value
        return self

    def with_os(self, value):
        self._os = value
        return self

    def build(self):
        if not all([self._cpu, self._memory, self._storage]):
            raise ValueError("cpu、memory、storage 是必填项")

        return Computer(
            cpu=self._cpu,
            memory=self._memory,
            storage=self._storage,
            gpu=self._gpu,
            os=self._os,
            wifi=self._wifi,
            bluetooth=self._bluetooth,
        )


computer = (
    ComputerBuilder()
    .with_cpu("Intel i7")
    .with_memory("32GB")
    .with_storage("1TB SSD")
    .with_gpu("RTX 5070")
    .with_os("Windows 11")
    .build()
)

print(computer)
```

### 怎么理解

现在 Builder 不是凭空造出一个“本来就很简单”的对象，而是在替调用者管理一个真实存在的重构造函数。

不用 Builder 时，调用方需要记住：

```text
cpu → memory → storage → gpu → os → wifi → bluetooth
```

有 Builder 后，调用代码变成：

```text
with_cpu(...)
   ↓
with_memory(...)
   ↓
with_storage(...)
   ↓
build()
```

每一步都有名字，因此“第 4 个参数是什么”这种记忆负担消失了；可选项也可以保留默认值。

还要注意：**Builder 和链式调用不是同一个概念**。链式调用只是常见写法；真正核心是把复杂创建过程拆成可读、可校验、可控制的步骤。

### 与《好代码，坏代码》的连接

Builder 可以降低：

- 参数顺序错误
- 大量可选参数造成的认知负担
- 构造函数职责过重

### 常见场景

- **复杂 HTTP 请求配置**：一步步设置请求头、认证、超时、重试、请求体，最后 `build()`。
- **测试数据构造**：`UserBuilder` 先给出合理默认值，测试只覆盖姓名、角色、地址等当前用到的字段。
- **复杂配置对象**：数据库连接配置同时有主机、端口、证书、连接池、超时等大量必填和可选项。

### 常见误用

如果对象只有两个简单字段：

```python
User(name, age)
```

直接构造通常比 Builder 更清楚。

还要注意：

- 不要把所有 setter 都叫 Builder；如果只是创建后随便修改字段，并没有复杂构造过程，收益很小。
- Builder 内部如果允许漏掉关键步骤，却在 `build()` 后才报错，会让错误更隐蔽。必要字段应尽早校验。
- Python 有关键字参数时，简单场景常常已经足够清楚：

```python
User(name="Tom", age=20)
```

不要为了“链式写法更酷”而增加一个 Builder。

---

## 4. Prototype —— 原型

### 解决什么问题

某个对象创建成本很高，但已有一个相似对象。

与其：

> 从头创建

不如：

> 复制现有对象。

这里的 **深拷贝** 可以先理解成：**不仅复制最外层对象，也把它内部引用的可变对象一起复制**。

Prototype 适合的重点并不只是“复制很方便”，而是：**从零创建这个对象需要做很多准备工作，而现在已经有一个合格模板**。

例如：

```python
report = Report()
report.load_default_style()
report.load_company_logo()
report.set_page_size("A4")
report.set_language("zh-CN")
```

如果每次新建报告都重复这些步骤，调用方既啰嗦又容易漏掉某一步。此时可以先准备好一个模板对象，再复制它：

```python
new_report = template.clone()
```

然后只修改少量不同的字段。

### Python 典型示例

```python
import copy


class Report:
    def __init__(self, title, style, sections):
        self.title = title
        self.style = style
        self.sections = sections

    def clone(self):
        return copy.deepcopy(self)


# 这份模板已经配置好了嵌套样式和固定章节。
template = Report(
    title="月度报告模板",
    style={
        "font": "Arial",
        "header": {"size": 18, "bold": True},
    },
    sections=["摘要", "关键指标", "风险"],
)

august_report = template.clone()
august_report.title = "8 月月度报告"
august_report.style["header"]["size"] = 20
august_report.sections.append("下月计划")

print(template.title)
print(template.style["header"]["size"])
print(august_report.title)
print(august_report.style["header"]["size"])
```

### 怎么理解

```text
复杂对象
   ↓ clone
复杂对象副本
```

可以把 Prototype 想成“**复制一份已经调好的模板，再改少量内容**”。

```text
模板对象
  ↓ clone
新对象
  ↓
只修改差异
```

它把“如何从零得到一个复杂对象”这件事藏在模板背后。

初学时最需要记住的是：Prototype 适合“相似对象很多、初始化复杂”，而不是“任何对象都应该有 `clone()`”。

### 与《好代码，坏代码》的连接

它可以隐藏复杂初始化过程。

调用者不需要知道：

```text
对象需要初始化哪些字段
需要加载哪些配置
需要建立哪些内部关系
```

### Python 提醒

Python 里通常直接使用：

```python
copy.copy()
copy.deepcopy()
```

所以不一定需要专门实现复杂的 Prototype 层次结构。

### 常见场景

- **报表模板**：先准备好公司 Logo、字体、固定章节和页眉的模板，每月复制后只改标题和数据。
- **工作流模板**：复制一份已经配置好的审批流程，再调整少量节点和负责人。
- **游戏对象模板**：大量敌人共享一套复杂初始配置，创建时复制模板再修改位置、生命值等差异。

### 常见误用

- **对象创建本来就很便宜，却统一加 `clone()`**：只是多了一套复制语义。
- **没想清楚浅拷贝和深拷贝**：内部有 `list`、`dict` 等可变对象时，两个副本可能意外共享数据。
- **复制了不应该复制的资源**：例如数据库连接、文件句柄、线程等，通常不能简单 `deepcopy`。

Prototype 最适合复制“数据型、模板型对象”，不等于“任何实例都安全可复制”。

---

## 5. Singleton —— 单例

### 解决什么问题

保证：

> **某个类只有一个实例。**

这里的 **实例** 就是“根据某个类真正创建出来的对象”。

Singleton 想解决的是：某些资源如果被创建很多份，可能会造成状态不一致或资源浪费。例如两份“全局配置对象”各自保存不同值，就会让代码很难判断到底该相信哪一份。

最直观的坏情况可以想成：

```python
config_a = Config()
config_b = Config()

config_a.debug = True
print(config_b.debug)  # 到底应该是什么？
```

Singleton 通过限制创建，让所有使用者拿到同一个对象。不过，“全局只需要一个”并不自动意味着“一定要使用 Singleton”，这一点后面尤其要警惕。

### Python 典型示例

```python
class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance


a = Singleton()
b = Singleton()

print(a is b)
```

输出：

```text
True
```

### 怎么理解

Singleton 可以想成“**整个程序都去同一个服务窗口取同一份对象**”。

无论谁调用：

```python
Singleton()
```

拿到的都是同一个实例。

但它有一个重要副作用：对象看起来像普通类，实际上却带着“全局共享”的性质。也就是说，一个地方修改它，另一个地方可能受到影响。因此理解 Singleton 时，要同时记住“唯一”与“共享状态”这两面。

### 常见场景

- **应用配置**：整个进程只维护一份已经加载的配置对象。
- **日志管理器**：多个模块共用同一个日志配置和输出入口。
- **资源管理器**：程序只保留一个统一管理某类共享资源的协调对象。

### 与《好代码，坏代码》的连接

这里尤其要警惕：

> Singleton 很容易变成隐藏的全局状态。

这会导致：

- 测试困难
- 生命周期（对象从创建到不再使用的这段过程）不清晰
- 代码隐式依赖
- 模块之间高度耦合

### Python 中更常见的做法

Python 模块本身就是单例式加载：

```python
# config.py
settings = {}
```

因此很多时候根本不需要自己实现 Singleton。

### 常见误用

- 把“我现在只需要一个对象”误认为“这个类永远只能有一个对象”。
- 用 Singleton 方便地访问数据库、配置、缓存，结果所有模块都形成隐藏依赖。
- 测试时无法轻易替换实例，导致测试互相影响。

Python 中如果只是共享配置，模块级对象往往更直接；如果还需要方便测试，显式把依赖作为参数传入通常更清楚。

---

# 二、结构型模式

结构型模式关注：

> **对象和类应该怎样组合？**

共 7 个：

- Adapter
- Bridge
- Composite
- Decorator
- Facade
- Flyweight
- Proxy

---

## 6. Adapter —— 适配器

### 解决什么问题

已经存在一个类：

```python
old_printer.print_text()
```

但新系统要求：

```python
printer.print()
```

两个接口不兼容。

Adapter 做：

> **接口转换。**

这里的 **接口** 不一定指 Python 里的某种特殊语法；对初学者来说，可以先把它理解成：**别人应该用什么方法、参数来调用你**。

Adapter 解决的是“两个东西本来都能工作，但说的不是同一种调用语言”。

例如新业务统一要求：

```python
printer.print("hello")
```

但旧组件只能这样用：

```python
old_printer.print_text("hello")
```

如果每个业务调用处都自己判断并转换：

```python
if isinstance(printer, OldPrinter):
    printer.print_text(text)
else:
    printer.print(text)
```

兼容代码就会散落到整个项目。Adapter 把这种转换集中在一个边界对象里。

### Python 典型示例

```python
class OldPrinter:
    def print_text(self, text):
        print(f"OldPrinter: {text}")


class PrinterAdapter:
    def __init__(self, old_printer):
        self.old_printer = old_printer

    def print(self, text):
        self.old_printer.print_text(text)


old = OldPrinter()
printer = PrinterAdapter(old)

printer.print("Hello")
```

### 怎么理解

```text
客户端
  ↓
Adapter
  ↓
旧系统
```

Adapter 最像现实里的转接头：

```text
新插头 → 转接头 → 旧插座
```

插头和插座本身都不用改，转接头只负责把一边的形式翻译成另一边能接受的形式。

所以判断是否需要 Adapter 时，最关键的问题不是“这个类旧不旧”，而是：

> 两边能力基本匹配，只是调用方式不兼容吗？

如果答案是“是”，Adapter 就很贴切。

### 与《好代码，坏代码》的连接

Adapter 的价值是：

> **把“脏兼容逻辑”集中在边界。**

而不是让业务代码里到处出现：

```python
if old_api:
    ...
else:
    ...
```

### 常见场景

- **第三方支付 SDK 接入**：旧 SDK 是 `make_payment(total)`，系统统一要求 `pay(amount)`，用 Adapter 转换。
- **旧日志接口迁移**：老模块调用 `write_log()`，新系统统一使用 `logger.info()`。
- **外部数据格式接入**：第三方返回字段名和内部模型不同，在边界处统一转换后再进入业务代码。

### 常见误用

- **Adapter 里面塞进大量新业务逻辑**：Adapter 应主要负责转换调用方式，而不是逐渐变成第二套业务系统。
- **明明可以直接修改自己控制的旧接口，却额外永久保留适配层**：如果迁移成本很低，直接统一接口可能更简单。
- **把 Facade 当 Adapter**：Adapter 重点是“接口不兼容”，Facade 重点是“接口太复杂”。

一句判断：两边本来能力相近，只是调用形式对不上，才优先想到 Adapter。

---

## 7. Bridge —— 桥接

### 解决什么问题

当系统有两个彼此独立变化的维度时，如果全部依赖继承组合，会产生“类爆炸”。

例如：

```text
BasicTVRemote
AdvancedTVRemote
BasicRadioRemote
AdvancedRadioRemote
```

Bridge 把：

> 抽象

和：

> 实现

拆开。

这里的两个词可以这样理解：

- **抽象**：上层只规定“要做什么”，先不绑定具体设备怎么做。
- **实现**：真正完成工作的那一侧，例如 TV、Radio。

Bridge 常出现在“两个维度都可能不断增加”的场景。比如遥控器有基础版、高级版；设备又有电视、收音机。

如果完全靠继承组合，容易出现：

```text
BasicTVRemote
AdvancedTVRemote
BasicRadioRemote
AdvancedRadioRemote
...
```

以后再加 `Projector` 和 `VoiceRemote`，组合数量继续增长。Bridge 的目标是让“遥控器种类”和“设备种类”分别扩展，而不是为每一种组合创建一个新类。

### Python 典型示例

```python
class TV:
    def turn_on(self):
        print("电视打开")

    def set_volume(self, value):
        print(f"电视音量: {value}")


class Radio:
    def turn_on(self):
        print("收音机打开")

    def set_volume(self, value):
        print(f"收音机音量: {value}")


class BasicRemote:
    def __init__(self, device):
        self.device = device

    def turn_on(self):
        self.device.turn_on()


class AdvancedRemote(BasicRemote):
    def mute(self):
        self.device.set_volume(0)


basic_tv = BasicRemote(TV())
advanced_radio = AdvancedRemote(Radio())

basic_tv.turn_on()
advanced_radio.turn_on()
advanced_radio.mute()
```

### 怎么理解

Bridge 的核心可以记成一句话：

> **不要提前把两个变化维度做成所有可能的组合类。**

这个示例里，两条变化轴都真实出现了：

```text
遥控器：BasicRemote / AdvancedRemote
设备：  TV / Radio
```

`BasicRemote(TV())`、`AdvancedRemote(Radio())` 是运行时组合出来的，而不是提前创建 `BasicTVRemote`、`AdvancedRadioRemote` 这类组合子类。

遥控器负责“用户想做什么”，设备负责“具体怎么执行”。遥控器内部保存一个设备对象，这就是 **组合**：一个对象把另一个对象作为自己的成员来使用，而不是靠继承把两者绑死。

### 可以怎样扩展

```text
Remote
 ├── BasicRemote
 └── AdvancedRemote

Device
 ├── TV
 └── Radio
```

两条继承/变化轴独立发展。

### 与《好代码，坏代码》的连接

Bridge 本质上在应用：

> **组合优于继承。**

### 常见场景

- **消息类型 × 发送渠道**：普通通知、告警通知独立于 Email、短信等发送渠道，两边可以分别增加。
- **图形 × 渲染方式**：`Circle/Rectangle` 独立于 SVG、Canvas 等绘制后端。
- **遥控器 × 设备**：基础遥控器、高级遥控器可以分别控制电视、收音机、投影仪。

### 常见误用

- 只有一个变化维度，却提前拆成“抽象层 + 实现层”，会增加跳转和类数量。
- 两个维度其实并不独立，强行拆开后反而需要大量特殊判断重新粘回去。
- 看到“组合优于继承”就一律使用 Bridge。组合只是手段，Bridge 特别针对“两条独立变化轴”。

如果系统只有 `TV + Remote` 一个组合，而且短期没有第二种设备或遥控器，直接组合通常已经够了。

---

## 8. Composite —— 组合

### 解决什么问题

希望：

> 单个对象

和：

> 对象集合

拥有相同的使用方式。

最经典例子：

- 文件
- 文件夹

这里的 **树形结构** 可以直觉理解成：**对象里面还能继续包含同类对象，像文件夹套文件夹一样形成层级**。

Composite 解决的是调用方不想反复区分“这是一个单独对象，还是一组对象”。

没有统一接口时，常会出现：

```python
if isinstance(item, File):
    item.show()
elif isinstance(item, Folder):
    for child in item.children:
        child.show()
```

层级再深一点，调用方就要继续写递归和类型判断。Composite 让 `File` 和 `Folder` 都提供相同操作，使调用者只需要说：

```python
item.show()
```

至于里面是一项还是很多项，由对象自己处理。

### Python 典型示例

```python
class File:
    def __init__(self, name):
        self.name = name

    def show(self, indent=0):
        print(" " * indent + self.name)


class Folder:
    def __init__(self, name):
        self.name = name
        self.children = []

    def add(self, item):
        self.children.append(item)

    def show(self, indent=0):
        print(" " * indent + self.name)

        for child in self.children:
            child.show(indent + 2)


root = Folder("root")

root.add(File("a.txt"))
root.add(File("b.txt"))

src = Folder("src")
src.add(File("main.py"))

root.add(src)

root.show()
```

输出：

```text
root
  a.txt
  b.txt
  src
    main.py
```

### 怎么理解

```text
Folder
├── File
├── File
└── Folder
    └── File
```

调用者不需要大量判断：

```python
if isinstance(node, File):
    ...
elif isinstance(node, Folder):
    ...
```

Composite 最关键的感觉是：

> **调用者把“一个”和“一组”当成同一种东西来用。**

`File.show()` 自己显示自己；`Folder.show()` 显示自己后，再让每个孩子执行同样的 `show()`。

这里出现的 **递归** 可以简单理解成：一个操作在处理子对象时，再次调用同一种操作。文件夹里还能有文件夹，所以天然适合这种结构。

### 与《好代码，坏代码》的连接

Composite 可以降低调用方的认知负担：

> 不管你是叶子节点（没有子节点的单个对象）还是组合节点（还能包含其他节点的对象），我都用同一种接口。

### 常见场景

- **文件系统**：`File` 和 `Folder` 都支持 `show()`、`size()`，文件夹内部还能继续包含文件夹。
- **后台菜单树**：菜单项和子菜单都用同一种接口渲染，子菜单再包含更多菜单项。
- **组织架构树**：员工和部门都能参与统一的“显示层级 / 统计人数”等操作。

### 常见误用

- 子节点和组合节点根本没有共同操作，却硬要求统一接口，会产生很多空方法。
- 为了统一调用，把只有 `Folder` 才合理的 `add()` 也放到 `File` 上，会让接口变得奇怪。
- 树结构很浅、调用方几乎不需要区分节点类型时，Composite 可能只是增加抽象。

它最适合“天然是层级结构，而且调用者真的希望统一处理叶子和容器”的场景。

---

## 9. Decorator —— 装饰器

### 解决什么问题

在：

> 不修改原对象

的情况下动态增加功能。

这里的 **动态增加功能** 指的是：**运行时把功能一层层包到现有对象外面，而不是提前创建所有组合类**。

例如咖啡可能有牛奶、糖、奶油三种附加项。如果靠继承，你很快会需要：

```text
MilkCoffee
SugarCoffee
MilkSugarCoffee
CreamCoffee
MilkCreamCoffee
...
```

组合越多，类越多。

Decorator 允许把功能拆成独立的小包装：

```python
coffee = MilkDecorator(Coffee())
coffee = SugarDecorator(coffee)
```

这样“牛奶”和“糖”各自只实现一次，再自由组合。

### Python 典型示例

```python
class Coffee:
    def cost(self):
        return 10


class MilkDecorator:
    def __init__(self, coffee):
        self.coffee = coffee

    def cost(self):
        return self.coffee.cost() + 2


class SugarDecorator:
    def __init__(self, coffee):
        self.coffee = coffee

    def cost(self):
        return self.coffee.cost() + 1


coffee = Coffee()
coffee = MilkDecorator(coffee)
coffee = SugarDecorator(coffee)

print(coffee.cost())
```

结果：

```text
13
```

### 怎么理解

Decorator 可以想成给对象一层层穿衣服：

```text
原对象
  ↓
牛奶层
  ↓
糖层
```

每一层都先调用里面那一层，再额外做一点事情。

它和继承最大的差别在于：继承通常在“定义类时”决定能力，Decorator 可以在“程序运行时”自由组合能力。

### 结构

```text
Sugar(
    Milk(
        Coffee()
    )
)
```

### 与《好代码，坏代码》的连接

如果你使用继承：

```text
Coffee
MilkCoffee
SugarCoffee
MilkSugarCoffee
...
```

组合数量很快爆炸。

Decorator 把不同功能独立组合。

### Python 提醒

Python 的：

```python
@decorator
def foo():
    ...
```

和 GoF Decorator 思想相关，但不完全等同。

### 常见场景

- **HTTP 客户端增强**：在原请求客户端外依次包上“日志 → 重试 → 缓存”能力，而不创建各种组合子类。
- **数据流处理**：基础流外面按需叠加压缩、加密、缓冲等能力。
- **仓储访问增强**：在原数据访问对象外包一层缓存或调用日志，不修改原对象。

### 常见误用

- 装饰层太多，调试时很难看出真实调用经过了哪些对象。
- Decorator 改变了原接口语义，而不仅是增强行为，调用者会产生意外。
- 只有一个固定增强功能时，直接在原类中清楚实现可能比多一层包装更简单。

另外，Python 函数装饰器和 GoF Decorator 思想相近，但一个主要包装可调用对象，一个经典模式常讨论对象组合，不要把两者完全画等号。

---

## 10. Facade —— 外观

### 解决什么问题

底层系统很复杂：

```text
CPU
Memory
Disk
Network
...
```

但使用者只想：

```python
computer.start()
```

Facade 提供：

> **一个简单入口。**

这里的 **子系统** 可以理解成：**为了完成一件事，内部需要协作的一组类或组件**。

Facade 解决的不是底层代码“不能用”，而是调用方为了做一件普通事情，被迫知道太多步骤。

例如没有 Facade 时：

```python
cpu.start()
memory.load()
disk.read()
network.connect()
```

如果启动顺序改变，所有调用者都可能需要跟着修改。

Facade 把这些细节藏在一个更符合使用者目标的方法后面：

```python
computer.start()
```

调用方只需要理解“启动电脑”，而不需要理解启动电脑内部每一步。

### Python 典型示例

```python
class CPU:
    def start(self):
        print("CPU 启动")


class Memory:
    def load(self):
        print("内存加载")


class Disk:
    def read(self):
        print("读取硬盘")


class ComputerFacade:
    def __init__(self):
        self.cpu = CPU()
        self.memory = Memory()
        self.disk = Disk()

    def start(self):
        self.cpu.start()
        self.memory.load()
        self.disk.read()


computer = ComputerFacade()
computer.start()
```

### 怎么理解

Facade 可以想成酒店前台。

客人只说：

```text
“帮我办理入住”
```

前台内部再协调登记、房卡、押金、房间状态。客人不需要逐个找这些部门。

所以 Facade 不是把底层系统删除，而是在它前面增加一个更适合调用者理解的入口。底层复杂性仍然存在，只是被放到了更合适的位置。

### 与《好代码，坏代码》的连接

Facade 是降低认知负担非常直接的模式。

调用者不需要知道：

```text
CPU.start()
Memory.load()
Disk.read()
```

只需要知道：

```python
computer.start()
```

这就是好的抽象边界。

### 常见场景

- **下单入口**：`checkout()` 内部协调库存检查、扣款、创建物流单，调用方只关心“完成下单”。
- **应用启动**：`app.start()` 内部初始化配置、数据库、缓存、后台任务。
- **文件转换服务**：`converter.convert()` 内部协调读取、解码、转换、写出等多个组件。

### 常见误用

- Facade 逐渐塞入所有业务逻辑，最后变成一个巨型类。
- 只是把十个底层方法原样转发成十个同名方法，并没有真正简化接口。
- 底层本来已经很简单，却又套一层 Facade，增加无意义跳转。

好的 Facade 应该让调用者“需要知道的概念更少”，而不只是“文件多一层”。

---

## 11. Flyweight —— 享元

### 解决什么问题

系统中存在大量：

> 内容重复

的对象。

可以共享不变部分，减少内存。

这里的 **共享** 不是“大家随便修改同一个对象”，而是：**把大量对象中相同、且通常不变的部分只保存一份**。

例如一个文档里有十万个字符，如果每个字符对象都各自保存：

```python
font = "Arial"
size = 12
color = "black"
```

这些重复数据会占用很多内存。

Flyweight 会把相同样式提取成共享对象，让许多字符只引用同一份样式。它解决的是“对象数量巨大 + 重复数据明显”时的内存问题，而不是普通代码的结构问题。

### Python 典型示例

```python
class CharacterStyle:
    def __init__(self, font, size, color):
        self.font = font
        self.size = size
        self.color = color


class StyleFactory:
    _styles = {}

    @classmethod
    def get_style(cls, font, size, color):
        key = (font, size, color)

        if key not in cls._styles:
            cls._styles[key] = CharacterStyle(font, size, color)

        return cls._styles[key]


class Character:
    def __init__(self, char, position, style):
        self.char = char          # 每个字符自己的数据
        self.position = position  # 每个字符自己的数据
        self.style = style        # 大量字符共享的数据


shared_style = StyleFactory.get_style("Arial", 12, "black")

c1 = Character("H", 0, shared_style)
c2 = Character("i", 1, StyleFactory.get_style("Arial", 12, "black"))

print(c1.style is c2.style)
```

### 怎么理解

Flyweight 可以拆成两部分理解：

```text
每个字符都不同的部分 → char、position，各自保存
很多字符都相同的部分 → font、size、color，共享一份
```

示例里的 `c1` 和 `c2` 是两个不同字符，但它们的 `style` 指向同一个 `CharacterStyle` 对象。

经典术语会把这两类数据叫做“外部状态”和“内部状态”，初学阶段不必背术语；先抓住“不同的自己留着，相同的抽出来共享”即可。

它是一种用额外结构换内存的优化，所以只有对象数量足够大时才值得。

### 常见场景

- **富文本编辑器**：成千上万个字符共享同一份字体、字号、颜色样式对象。
- **大型游戏地图**：成千上万棵树共享同一份“树的外观数据”，每棵树只保存自己的位置。
- **图标列表**：大量相同图标实例共享不可变的图标数据，只保留各自的位置或状态。

### 注意

不要因为“想省一点内存”就提前使用 Flyweight。

它通常属于：

> **性能问题已经实际出现之后再考虑的优化。**

### 常见误用

- 没有测量内存问题，就为了“设计模式完整”提前引入缓存和共享池。
- 共享对象本身是可变的，某个地方一修改，所有使用者都被影响。
- 为了省很少内存，引入复杂的查找和生命周期管理，反而让代码更难维护。

Flyweight 通常属于有数据证明之后再做的优化。

---

## 12. Proxy —— 代理

### 解决什么问题

不希望调用者直接访问真实对象。

需要一个对象：

> **代替真实对象，控制访问。**

这里的 **代理对象** 可以理解成：**调用者以为自己在使用真实对象，其实中间先经过一个代办者**。

为什么需要代办者？因为有些操作不应该每次都直接做，例如大图片加载很慢、远程请求很贵、某些操作需要先检查权限。

不用 Proxy 时可能直接：

```python
image = RealImage("photo.jpg")  # 创建时立刻加载
```

即使最后根本没有显示图片，也已经付出了加载成本。

有 Proxy 后：

```python
image = ImageProxy("photo.jpg")
```

先创建一个很轻的代理，真正需要 `display()` 时才创建真实图片。

### Python 典型示例

```python
class RealImage:
    def __init__(self, filename):
        print("加载大图片...")
        self.filename = filename

    def display(self):
        print("显示", self.filename)


class ImageProxy:
    def __init__(self, filename):
        self.filename = filename
        self.image = None

    def display(self):
        if self.image is None:
            self.image = RealImage(self.filename) # 赋值给 self.image

        self.image.display()


image = ImageProxy("photo.jpg")

print("对象已经创建")

image.display()
```

### 怎么理解

创建：

```python
ImageProxy("photo.jpg")
```

不会马上加载大图片。

真正执行：

```python
image.display()
```

时才创建 `RealImage`。

Proxy 最关键的是：**调用者仍然使用同样的操作，但代理决定什么时候、能不能、要不要真正转给真实对象**。

流程可以理解为：

```text
调用者
  ↓ display()
Proxy
  ↓ 先检查 / 缓存 / 延迟
RealImage
```

因此 Proxy 的重点在“访问控制”，真实对象可能甚至还没有被创建。

### 常见场景

- **图片延迟加载**：列表里先放轻量代理，真正滚动到图片时才加载大图。
- **权限代理**：调用 `delete_user()` 前先由代理检查当前用户是否有管理员权限。
- **远程服务代理**：调用方式看起来像本地对象，代理内部负责真正的网络请求、缓存或重试。

### Decorator vs Proxy

```text
Decorator = 增强功能
Proxy     = 控制访问
```

### 常见误用

- Proxy 自己做了大量与访问控制无关的业务逻辑，逐渐失去“代办者”角色。
- 代理和真实对象表现差异太大，调用者以为是普通本地调用，实际上一次调用可能触发很慢的网络请求。
- 为了每个对象都“加一层安全感”而创建 Proxy，会让调用链无意义变长。

如果目的只是“增加功能”，更像 Decorator；如果目的是“控制何时、是否、以什么方式访问真实对象”，才更像 Proxy。

---

# 三、行为型模式

行为型模式关注：

> **对象之间怎样协作？**

共 11 个：

- Iterator
- Template Method
- Strategy
- Visitor
- Chain of Responsibility
- Mediator
- Observer
- Memento
- State
- Command
- Interpreter

---

## 13. Iterator —— 迭代器

### 解决什么问题

不暴露集合内部结构，也能够：

> 依次访问元素。

这里的 **集合内部结构** 指的是“数据到底存在哪里、用什么方式组织”，例如 `list`、树、数据库查询结果。

Iterator 解决的是：调用者只想一个一个拿元素，不想知道底层到底怎么存。

如果没有统一的遍历方式，不同结构可能要求不同代码：

```python
# list
for i in range(len(items)):
    print(items[i])

# 某种自定义结构
node = tree.first()
while node:
    print(node.value)
    node = node.next()
```

Iterator 把这些差异藏起来，让调用者统一使用“给我下一个元素”的方式。Python 已经把这件事做进了 `for` 循环，所以你经常是在“使用迭代器思想”，而不是手写经典 GoF 结构。

### Python 典型示例

```python
class BookShelf:
    def __init__(self):
        self.books = []

    def add(self, book):
        self.books.append(book)

    def __iter__(self):
        return iter(self.books)


shelf = BookShelf()
shelf.add("Python")
shelf.add("Design Patterns")

for book in shelf:
    print(book)
```

### 怎么理解

Python 中理解 Iterator，最实用的方法就是观察：

```python
for book in shelf:
    print(book)
```

`for` 循环并不需要知道 `BookShelf` 内部是 `list`。它只要求这个对象能够按迭代规则不断提供元素。

这里的 **协议** 可以理解成：**大家约定好一套方法，只要你按这个约定实现，语言就知道怎么使用你**。

因此 `__iter__()` 的意义就是让自定义对象接入 Python 已经存在的遍历机制。

### Python 为什么特别重要

Python 已经把 Iterator 深度集成进语言：

```python
for item in items:
    ...
```

背后就是迭代协议。

### 与《好代码，坏代码》的连接

调用者只关心：

```text
“给我下一个元素”
```

而不关心：

```text
底层是 list
tree
database cursor（数据库查询结果逐条读取的位置指针）
generator（生成器：需要一个值时才产生一个值的 Python 对象）
```

这是典型的信息隐藏。

### 常见场景

- **分页 API**：调用方写 `for item in client.items()`，迭代器内部自动请求下一页。
- **树结构遍历**：调用方依次拿节点，不需要自己维护栈或递归细节。
- **数据库结果流**：查询结果很大时一条条读取，而不是一次把全部数据装进内存。

### 常见误用

- 为普通 `list` 再手写一套复杂 Iterator 类，通常没有必要。
- 在迭代过程中随意修改底层集合，可能导致元素跳过或行为难以预测。
- 把“Iterator 模式”误解成“所有循环都要封装”。

Python 项目里，多数时候优先正确实现 `__iter__()` 或使用生成器即可。

---

## 14. Template Method —— 模板方法

### 解决什么问题

多个流程整体相同，但其中一两个步骤不同。

例如：

```text
读取
处理
保存
```

只有“处理”方式不同。

这里的 **流程骨架** 可以理解成：**一件事的大步骤和顺序固定，但其中少数步骤允许替换**。

例如导入文件时，大流程都是：

```text
读取文件 → 解析内容 → 保存结果
```

如果 CSV 和 JSON 只有“解析内容”不同，却分别复制整套流程：

```python
def process_csv():
    read()
    parse_csv()
    save()

def process_json():
    read()
    parse_json()
    save()
```

那么以后修改 `read()` 或 `save()` 时，很容易漏改其中一个。

Template Method 把固定顺序放在父类，只把会变化的步骤留给子类。

### Python 典型示例

```python
from abc import ABC, abstractmethod


class DataProcessor(ABC):
    def process(self):
        self.read()
        self.handle()
        self.save()

    def read(self):
        print("读取数据")

    @abstractmethod
    def handle(self):
        pass

    def save(self):
        print("保存数据")


class CSVProcessor(DataProcessor):
    def handle(self):
        print("处理 CSV")


class JSONProcessor(DataProcessor):
    def handle(self):
        print("处理 JSON")


CSVProcessor().process()
```

### 怎么理解

Template Method 可以想成“**老师规定答题模板，学生只填写其中几道可变题**”。

父类的 `process()` 固定调用顺序：

```text
read → handle → save
```

子类只决定 `handle()`。

这种设计适合“整体流程稳定、变化点很少”。如果后来每一步都可能独立变化，继续靠子类继承就会越来越僵硬。

### 结构

```text
read
 ↓
handle   ← 子类变化
 ↓
save
```

### 与《好代码，坏代码》的连接

Template Method 把：

> 稳定部分

和：

> 变化部分

分离。

### 注意

它依赖继承。

如果变化越来越复杂，经常可以考虑：

> Strategy + 组合

代替。

### 常见场景

- **CSV / JSON 导入**：固定“读取 → 解析 → 校验 → 保存”流程，只替换解析步骤。
- **文件导出任务**：固定“准备数据 → 格式化 → 写文件 → 上传”，不同格式只改格式化步骤。
- **测试生命周期**：固定“准备环境 → 执行测试 → 清理环境”，具体测试只实现中间步骤。

### 常见误用

- 子类为了改变流程顺序，大量覆盖模板方法，说明“固定骨架”其实并不稳定。
- 父类提供太多“可覆盖的小步骤”，让使用者必须读完整继承层次才能理解执行流程。
- 明明只是想替换一个算法，却建立多层子类；这种情况 Strategy 往往更轻。

使用前先确认：真正稳定的是流程顺序，而不是仅仅“代码看起来相似”。

---

## 15. Strategy —— 策略

### 解决什么问题

一个业务流程中有：

> 多种可替换算法。

例如支付：

```text
支付宝
微信
信用卡
```

这里的 **算法** 不必理解得很数学；它只是指：**完成同一个目标时，可以互相替换的一种做法**。

例如“付款”这个目标不变，但付款方式可能变化：

```python
if payment_type == "card":
    pay_by_card(amount)
elif payment_type == "alipay":
    pay_by_alipay(amount)
elif payment_type == "wechat":
    pay_by_wechat(amount)
```

刚开始只有两三种时并不严重，但当每种支付还有自己的校验、退款、测试逻辑时，一个大条件分支会越来越难维护。

Strategy 把每种做法单独放到一个对象里，订单只依赖共同的 `pay()` 行为。

### Python 典型示例

```python
class CreditCardPayment:
    def pay(self, amount):
        print(f"信用卡支付 {amount}")


class AlipayPayment:
    def pay(self, amount):
        print(f"支付宝支付 {amount}")


class Order:
    def __init__(self, payment):
        self.payment = payment

    def checkout(self, amount):
        self.payment.pay(amount)


order = Order(AlipayPayment())
order.checkout(100)
```

### 怎么理解

Strategy 的思考方式是：

```text
Order 负责“什么时候付款”
PaymentStrategy 负责“具体怎么付款”
```

也就是说，把“使用算法的人”和“算法本身”拆开。

Python 里策略不一定非得写成很多类；简单情况下，函数本身也可以作为策略传入。UML 是“用图表示类和它们之间关系”的常见画法；模式的重点是“可替换”，不是“必须长成某个 UML 结构”。

### 它替代什么坏代码

例如：

```python
if payment == "alipay":
    ...
elif payment == "wechat":
    ...
elif payment == "card":
    ...
```

随着策略增加：

- `if/elif` 越来越长
- 修改风险越来越大
- 测试组合越来越难

Strategy 把算法拆成独立对象。

### 与《好代码，坏代码》的连接

这是非常值得优先掌握的模式。

它体现：

> **把变化隔离到独立组件里。**

同时也非常利于单元测试。

### 常见场景

- **支付方式**：订单流程不变，支付算法可以换成信用卡、支付宝、微信。
- **运费计算**：同一个订单根据快递公司或配送方式选择不同计费策略。
- **折扣规则**：会员价、优惠券、节日折扣各自实现同一 `calculate()` 接口。

### 常见误用

- 只有两个非常简单、几乎不会变化的分支，也拆成多个类，代码反而更难追。
- 每个策略接口完全不同，使用策略的对象仍然到处 `isinstance` 判断，那并没有真正做到可替换。
- 策略对象之间复制大量共同逻辑，却没有提取共享代码。

Python 中简单策略用函数就够时，不必为了模式形式强行建类。

---

## 16. Visitor —— 访问者

### 解决什么问题

数据结构比较稳定，但：

> 经常需要增加新的操作。

例如：

```text
File
Folder
```

未来不断增加：

```text
打印
统计大小
搜索
导出
权限检查
```

这里的 **数据结构稳定** 指的是：**对象种类不常增加，但针对这些对象要做的新事情经常增加**。

例如系统长期只有 `File` 和 `Folder` 两种节点，但不断新增：

```text
打印
统计大小
导出
权限检查
```

如果每新增一个操作，都往 `File` 和 `Folder` 里塞新方法，这两个类会不断膨胀。

Visitor 反过来把“操作”放到独立对象中：

```python
PrintVisitor()
SizeVisitor()
ExportVisitor()
```

这样增加一种操作时，主要新增一个 Visitor，而不是修改所有业务流程。

### Python 典型示例

```python
class File:
    def __init__(self, name, size):
        self.name = name
        self.size = size

    def accept(self, visitor):
        return visitor.visit_file(self)


class Folder:
    def __init__(self, name):
        self.name = name

    def accept(self, visitor):
        return visitor.visit_folder(self)


class PrintVisitor:
    def visit_file(self, file):
        return f"文件: {file.name}"

    def visit_folder(self, folder):
        return f"文件夹: {folder.name}"


class SummaryVisitor:
    def visit_file(self, file):
        return f"{file.name}: {file.size} KB"

    def visit_folder(self, folder):
        return f"{folder.name}: 目录"


nodes = [File("main.py", 12), Folder("src")]

for node in nodes:
    print(node.accept(PrintVisitor()))
    print(node.accept(SummaryVisitor()))
```

### 怎么理解

Visitor 可以理解成“**数据对象负责接待，Visitor 负责带来一种新操作**”。

示例里 `File` 和 `Folder` 没有因为“打印”和“生成摘要”而各自增加两个新方法；它们只保留统一的：

```python
accept(visitor)
```

然后：

```text
PrintVisitor   = 一种操作
SummaryVisitor = 另一种操作
```

如果明天再增加 `ExportVisitor`，主要新增的是一个新的操作对象，而不是继续往 `File`、`Folder` 里塞方法。

这个模式有点反直觉，因为行为不再放在数据类内部。它的收益只在“对象类型很稳定、操作经常增加”时比较明显。

### 核心思想

把：

```text
数据结构
```

和：

```text
作用在数据上的操作
```

分离。

### Visitor 的代价

Visitor 很容易增加理解成本。

当：

> 数据类型本身经常变化

时，Visitor 反而会很痛苦。

因此它属于：

> 先理解，不要急着使用

的模式。

### 常见场景

- **文件树工具**：文件/文件夹类型稳定，但不断增加“打印、统计大小、导出、权限检查”等操作。
- **代码语法树工具**：节点类型较稳定时，可以分别增加格式化、检查、生成代码等 Visitor。
- **固定业务对象的多种报表**：对象类型很少变化，但经常增加新的统计或导出方式。

### 常见误用

- `File`、`Folder`、`Link` 等数据类型经常增加时，每个 Visitor 都要跟着修改，维护成本会很高。
- 操作只有一两个，却先引入 `accept()` 和一整套 Visitor 层次，收益不足。
- 为了“把方法移出类”而使用 Visitor，却没有“数据稳定、操作常变”的真实需求。

这是一个适用条件比较苛刻的模式，能识别比急着使用更重要。

---

## 17. Chain of Responsibility —— 责任链

### 解决什么问题

一个请求需要经过多个处理器。

每个处理器可以：

- 处理
- 拒绝
- 交给下一个

这里的 **处理器** 可以理解成：**负责检查或处理请求的一小段独立逻辑**。

责任链适合“一个请求要依次过好几关”的情况，例如：

```python
def process(request):
    check_login(request)
    check_permission(request)
    check_rate_limit(request)
    validate_data(request)
```

当检查越来越多，这个函数会知道所有步骤，而且很难复用其中一部分。

Chain of Responsibility 把每一关拆成一个处理器，并让处理器决定：

```text
我处理完继续往下传
或
我在这里停止
```

于是整条处理流程可以通过组合处理器来搭建。

### Python 典型示例

```python
class Handler:
    def __init__(self, next_handler=None):
        self.next = next_handler

    def handle(self, request):
        if self.next:
            self.next.handle(request)


class AuthHandler(Handler):
    def handle(self, request):
        if not request.get("user"):
            print("认证失败")
            return

        print("认证成功")
        super().handle(request)


class AdminHandler(Handler):
    def handle(self, request):
        if request.get("role") != "admin":
            print("权限不足")
            return

        print("权限验证成功")
        super().handle(request)


chain = AuthHandler(
    AdminHandler()
)

chain.handle({
    "user": "Tom",
    "role": "admin"
})
```

### 怎么理解

责任链最适合用“过关”理解：

```text
请求
 ↓
登录检查
 ↓
权限检查
 ↓
限流检查
 ↓
真正业务
```

每一关只负责自己的规则，不需要知道整条链的所有细节。

其中“传给下一个”是核心。如果某一关发现请求不应该继续，就可以直接停止，因此链本身也表达了业务处理顺序。

### 结构

```text
Request
   ↓
认证
   ↓
权限
   ↓
业务处理
```

### 常见场景

- **Web 请求中间件**：请求依次经过认证、日志、限流、参数校验，再进入真正业务。
- **表单校验链**：用户名、密码、邮箱、风控规则按顺序检查，任一步失败即可停止。
- **日志处理链**：不同级别或类型的日志依次交给能够处理它的 Handler。

### 与《好代码，坏代码》的连接

它可以避免：

```python
def process(request):
    auth()
    log()
    validate()
    check_permission()
    rate_limit()
    ...
```

所有逻辑都堆在一个巨型函数里。

### 常见误用

- 处理顺序其实是强业务规则，却被动态拼装得看不出来，导致行为难追踪。
- 某个 Handler 同时做认证、日志、权限、业务处理，拆链后仍然职责混杂。
- 请求最终没人处理，却没有明确兜底或错误提示。

责任链适合“一连串相对独立的处理步骤”，不是把一个大函数机械拆成很多小类。

---

## 18. Mediator —— 中介者

### 解决什么问题

对象之间彼此直接调用，形成复杂网络：

```text
A ↔ B
↕   ↕
C ↔ D
```

Mediator 引入一个中间协调者：

```text
A ─┐
B ─┼→ Mediator
C ─┤
D ─┘
```

这里的 **多对多耦合** 可以直觉理解成：**很多对象彼此都认识、彼此直接调用，关系线越来越多**。

例如一个界面中，输入框变化要通知按钮、列表和状态栏，按钮又会反过来修改输入框和列表。直接互调可能变成：

```text
Input → Button
Input → List
Button → Input
Button → List
List → Status
...
```

添加一个组件时，往往还要修改多个旧组件。

Mediator 让这些对象少直接认识彼此，而是把“谁变化后要协调谁”集中交给中介者。

### Python 典型示例

```python
class ChatRoom:
    def __init__(self):
        self.users = []

    def register(self, user):
        self.users.append(user)

    def send(self, sender, message):
        for user in self.users:
            if user is not sender:
                user.receive(sender.name, message)


class User:
    def __init__(self, name, chatroom):
        self.name = name
        self.chatroom = chatroom
        self.chatroom.register(self)

    def send(self, message):
        self.chatroom.send(self, message)

    def receive(self, sender_name, message):
        print(f"{self.name} 收到 {sender_name}: {message}")


room = ChatRoom()
tom = User("Tom", room)
jack = User("Jack", room)
alice = User("Alice", room)

tom.send("今晚 8 点开会")
```

### 怎么理解

Mediator 可以想成群聊里的“消息中心”。

没有中介者时，Tom 如果想通知 Jack 和 Alice，可能需要自己保存并调用这两个对象；人数增加后，每个 `User` 都越来越知道“还有哪些 User”。

示例里每个 `User` 只认识 `ChatRoom`：

```text
Tom ───┐
Jack ──┼→ ChatRoom → 决定把消息发给谁
Alice ─┘
```

所以减少的是对象之间的“直接认识”。协调规则不会消失，而是集中到了 Mediator。

### 与《好代码，坏代码》的连接

它降低：

> 多对多对象关系的耦合。

但也要注意：

> Mediator 自己可能膨胀成 God Object（“上帝对象”：一个什么都知道、什么都负责的超大对象）。

### 常见场景

- **复杂表单联动**：选择“企业用户”后，中介者统一决定显示公司字段、关闭个人字段、更新提交按钮状态。
- **聊天室**：用户只把消息交给 `ChatRoom`，不需要保存所有其他用户对象。
- **界面组件协调**：输入框、按钮、列表之间有大量联动时，把“谁变化后更新谁”集中到一个协调者。

### 常见误用

- 所有事件、所有业务判断都堆进一个 Mediator，最后变成 **God Object**。这个词可以理解成：**一个什么都知道、什么都负责的超大对象**。
- 原本只有两个对象简单互调，也强行加入中介者，增加不必要层次。
- Mediator 对组件内部细节知道太多，组件仍然很难独立变化。

好的 Mediator 是“协调关系集中”，不是“所有逻辑集中”。

---

## 19. Observer —— 观察者

### 解决什么问题

一个对象变化时，希望：

> 自动通知多个其他对象。

这里的 **订阅者** 可以理解成：**对某个变化感兴趣，并希望变化发生时收到通知的对象**。

如果天气站必须直接知道所有显示设备：

```python
def set_temperature(value):
    phone_display.update(value)
    web_display.update(value)
    logger.record(value)
```

以后每增加一个接收者，都要修改天气站。

Observer 让天气站只维护“订阅我的对象列表”。它只负责发通知，不需要把每个接收者的业务写死在自己内部。

### Python 典型示例

```python
class WeatherStation:
    def __init__(self):
        self.observers = []

    def subscribe(self, observer):
        self.observers.append(observer)

    def set_temperature(self, temperature):
        for observer in self.observers:
            observer.update(temperature)


class PhoneDisplay:
    def update(self, temperature):
        print(f"手机显示温度: {temperature}")


class WebDisplay:
    def update(self, temperature):
        print(f"网页显示温度: {temperature}")


station = WeatherStation()

station.subscribe(PhoneDisplay())
station.subscribe(WebDisplay())

station.set_temperature(30)
```

### 怎么理解

Observer 可以用“关注公众号”来理解：

```text
订阅
  ↓
主题发生变化
  ↓
统一通知所有订阅者
```

发布者只知道“我要通知这一组订阅者”，并不关心每个订阅者收到通知后具体做什么。

这种解耦很方便扩展接收者，但代价是调用路径从“直接调用”变成“事件触发”，调试时需要多追一层。

### 输出

```text
手机显示温度: 30
网页显示温度: 30
```

### 常见场景

- **订单已支付事件**：一次 `OrderPaid` 同时触发发邮件、加积分、扣库存，订单对象不直接调用这三个模块。
- **界面状态更新**：数据模型变化后，多个界面组件自动刷新。
- **缓存失效通知**：数据更新后通知多个缓存或索引组件清理旧数据。

### 与《好代码，坏代码》的连接

生产者不需要知道：

> 谁在使用我的事件。

这降低了直接依赖。

### 风险

事件链过多时会出现：

> “是谁触发了这个逻辑？”

所以 Observer 可能降低结构耦合，但增加运行时追踪难度。

### 常见误用

- 一个事件触发另一个事件，再触发第三个事件，形成很长的隐式链路，调试困难。
- 忘记取消订阅，长期运行程序里可能保留不需要的对象。
- 对执行顺序有严格要求，却依赖订阅者注册顺序，规则会很脆弱。
- 把所有函数调用都改成事件，虽然“解耦”了，但程序行为变得看不见。

Observer 适合“一对多通知”，不是“越少直接调用越先进”。

---

## 20. Memento —— 备忘录

### 解决什么问题

保存某个时刻的状态，以后恢复。

典型例子：

- Ctrl + Z
- 游戏存档
- 编辑器历史

这里的 **状态快照** 可以理解成：**把对象某一时刻的重要数据保存一份，之后可以回到那个时刻**。

最直接的例子是编辑器撤销。没有 Memento 时，你可能为了恢复旧内容，在外部代码里直接读取和保存对象内部字段：

```python
backup_text = editor.text
backup_cursor = editor.cursor
backup_selection = editor.selection
```

这样外部代码就越来越了解 `Editor` 的内部结构。

Memento 的目标是让对象自己负责“我要保存哪些状态”，外部只负责保存这份快照并在需要时交还。

### Python 典型示例

```python
class EditorMemento:
    def __init__(self, text, cursor):
        self.text = text
        self.cursor = cursor


class Editor:
    def __init__(self):
        self.text = ""
        self.cursor = 0

    def write(self, text):
        self.text = self.text[:self.cursor] + text + self.text[self.cursor:]
        self.cursor += len(text)

    def save(self):
        return EditorMemento(self.text, self.cursor)

    def restore(self, memento):
        self.text = memento.text
        self.cursor = memento.cursor


editor = Editor()
editor.write("Hello")
backup = editor.save()

editor.write(" World")
print(editor.text, editor.cursor)

editor.restore(backup)
print(editor.text, editor.cursor)
```

### 怎么理解

Memento 可以理解成编辑器的“完整存档点”：

```text
text="Hello", cursor=5
        ↓ save()
EditorMemento
        ↓
继续编辑成 "Hello World"
        ↓ restore()
恢复 text 和 cursor
```

重点是快照里保存的不只是一个随手复制的字符串，而是**恢复对象所需要的一组状态**。

外部代码只负责保管 `EditorMemento`，不需要自己记住“Editor 到底有哪些字段需要备份”。

因此它和 Command 的区别可以先这样记：Command 更像保存“做过哪一步操作”，Memento 更像保存“当时数据长什么样”。

### 核心

```text
当前状态
   ↓ save
Memento
   ↓ restore
恢复状态
```

### 注意

真实系统可能需要处理：

- 深拷贝
- 大对象状态
- 快照数量
- 持久化（把状态保存到文件或数据库，使程序重启后仍能读取）
- 版本兼容

### 常见场景

- **文本编辑器撤销**：保存文本、光标、选区等状态，执行编辑后可以恢复。
- **画布编辑器**：移动、缩放多个图形前保存快照，用户按撤销时回到旧状态。
- **表单草稿版本**：用户每次重要修改后保存一个草稿快照，需要时恢复某个版本。

### 常见误用

- 状态对象很大，却每一步都完整深拷贝，内存会快速增长。
- 快照里保存数据库连接、线程等不可简单恢复的外部资源。
- 需要的是“撤销一个动作”，却只保存全量状态，可能比 Command 更重。
- 数据结构升级后，旧快照无法恢复，却没有版本兼容方案。

先评估快照大小和保存频率，再决定是否适合 Memento。

---

## 21. State —— 状态

### 解决什么问题

一个对象：

> 在不同状态下行为完全不同。

例如订单：

```text
Pending
Paid
Shipped
Cancelled
```

这里的 **状态** 指的是：**对象当前所处的阶段，而这个阶段会改变它允许做什么、应该怎么做**。

例如订单处于不同阶段时，`cancel()` 的行为可能完全不同：

```python
if state == "pending":
    refund = False
elif state == "paid":
    refund = True
elif state == "shipped":
    raise ValueError("已发货，不能直接取消")
```

如果 `pay()`、`ship()`、`cancel()`、`refund()` 每个方法里都出现一套类似判断，状态规则就会散落在整个类里。

State 把“处于某个状态时应该怎么表现”集中到对应状态对象中。

### Python 典型示例

```python
class PendingState:
    def pay(self, order):
        print("支付成功")
        order.state = PaidState()

    def ship(self, order):
        print("还未支付，不能发货")


class PaidState:
    def pay(self, order):
        print("订单已经支付过了")

    def ship(self, order):
        print("订单发货")
        order.state = ShippedState()


class ShippedState:
    def pay(self, order):
        print("订单已经发货")

    def ship(self, order):
        print("订单已经发过货了")


class Order:
    def __init__(self):
        self.state = PendingState()

    def pay(self):
        self.state.pay(self)

    def ship(self):
        self.state.ship(self)


order = Order()
order.ship()  # 还未支付，不能发货
order.pay()   # 状态从 Pending 变成 Paid
order.ship()  # 状态从 Paid 变成 Shipped
```

### 怎么理解

State 的关键不是“把一个 `if` 拆成三个类”，而是：**同一个状态会影响对象的多个行为，而且状态还能按规则发生转换。**

示例里：

```text
Pending
  ├── pay()  → Paid
  └── ship() → 拒绝

Paid
  ├── pay()  → 告知已支付
  └── ship() → Shipped
```

`Order` 自己不再写一套 `if state == ...`；它把当前行为交给 `self.state`。

所以当状态很多，并且 `pay()`、`ship()`、`cancel()` 等多个方法都受状态影响时，State 才真正开始有价值。

### 它替代什么代码

```python
if state == "pending":
    ...
elif state == "paid":
    ...
elif state == "shipped":
    ...
```

如果每个状态内部还有很多不同操作，这类条件会迅速膨胀。

### Strategy vs State

```text
Strategy = 主动选择算法
State    = 当前状态决定行为
```

### 常见场景

- **订单生命周期**：待支付、已支付、已发货、已取消状态下，`pay()`、`ship()`、`cancel()` 行为不同。
- **上传任务**：等待、上传中、成功、失败状态决定“能否重试 / 能否取消 / 应显示什么提示”。
- **文档审批**：草稿、审核中、已通过、已驳回状态决定可执行的编辑和提交操作。

### 常见误用

- 只有一个简单布尔值 `is_enabled`，却创建 `EnabledState/DisabledState` 两个类。
- 状态转换规则散落在外部业务代码，状态对象只是换了个地方保存分支，并没有集中规则。
- 允许任意 `set_state()`，导致订单可以从 `Pending` 直接跳到 `Shipped`，破坏合法流程。

如果状态很多、每个状态影响多个行为，State 才更值得。

---

## 22. Command —— 命令

### 解决什么问题

把：

> 一个操作

包装成：

> 一个对象。

这里的 **把操作包装成对象** 可以直觉理解成：**原本一次函数调用，被变成一个可以保存、传递、稍后执行的东西**。

普通调用：

```python
light.on()
```

执行完就结束了。调用本身很难被放进队列、保存到历史记录或统一撤销。

Command 会先创建：

```python
command = LightOnCommand(light)
```

此时 `command` 就像一张“待办指令卡”。你可以先保存它、排队它，最后再：

```python
command.execute()
```

因此 Command 解决的重点是“把操作当数据管理”，而不是为了让一次简单调用看起来更面向对象。

### Python 典型示例

```python
class Light:
    def on(self):
        print("开灯")

    def off(self):
        print("关灯")


class LightOnCommand:
    def __init__(self, light):
        self.light = light

    def execute(self):
        self.light.on()

    def undo(self):
        self.light.off()


class LightOffCommand:
    def __init__(self, light):
        self.light = light

    def execute(self):
        self.light.off()

    def undo(self):
        self.light.on()


class RemoteControl:
    def __init__(self):
        self.history = []

    def execute(self, command):
        command.execute()
        self.history.append(command)

    def undo_last(self):
        if self.history:
            self.history.pop().undo()


light = Light()
remote = RemoteControl()

remote.execute(LightOnCommand(light))
remote.execute(LightOffCommand(light))
remote.undo_last()  # 撤销“关灯”，所以重新开灯
```

### 怎么理解

Command 可以把一次操作想成一张对象化的任务卡：

```text
任务卡里记录：
- 要调用谁
- 要做什么
- 怎么执行
- 必要时怎么撤销
```

示例里的 `RemoteControl` 不只“转发一次调用”，它还把执行过的 Command 放进 `history`。因此最后可以拿出上一条命令并执行 `undo()`。

这才体现出“把操作变成对象”的价值：操作现在能像普通数据一样被保存、排队、记录、撤销或重放。

### 为什么要这么绕

直接：

```python
light.on()
```

不是更简单吗？

如果只需要执行一次，确实更简单。

Command 的价值出现在需要：

- 保存命令
- 排队
- 延迟执行
- 日志
- Undo / Redo
- 重放操作

时。

### 与《好代码，坏代码》的连接

它把：

> “要做什么”

从：

> “什么时候做 / 谁触发”

中分离出来。

### 常见场景

- **编辑器 Undo / Redo**：插入文字、删除文字、移动图形都变成 Command，历史记录可以撤销和重放。
- **后台任务队列**：把“生成报表”“发邮件”包装成任务对象，先入队，稍后由工作进程执行。
- **菜单和快捷键共用操作**：菜单点击和 `Ctrl+S` 都触发同一个 `SaveCommand`。

### 常见误用

- 每个只有一行的方法都再包装成一个 Command 类，却没有队列、撤销、延迟等需求。
- Command 同时包含大量业务状态和流程，最后变成一个新的巨型类。
- 需要 Undo，却没有记录执行前信息或反向操作，只有 `execute()` 并不能自动获得撤销能力。

只有当“操作需要被当成数据管理”时，Command 的额外层次才值得。

---

## 23. Interpreter —— 解释器

### 解决什么问题

需要定义一个简单语言，并解释它。

例如：

```text
ADD 1 2
SUB 10 3
```

这里有几个容易吓到初学者的词：

- **Parser（解析器）**：把一段文本拆解成程序能够理解的结构。
- **AST（抽象语法树）**：用树形对象表示一段代码或表达式的结构。
- **DSL（领域特定语言）**：只为某个小领域设计的简单语言，例如查询规则或配置表达式。

Interpreter 适合的问题是：你的程序需要理解一套规模较小、规则相对固定的表达方式。

最简单时可能是一堆判断：

```python
if command == "ADD":
    ...
elif command == "SUB":
    ...
elif command == "MUL":
    ...
```

当语言规则继续增加，而且表达式之间可以组合时，单个 `if/elif` 会越来越难组织。Interpreter 把不同语法规则表示成对象，再让这些对象共同解释输入。

### Python 典型示例

```python
class NumberExpression:
    def __init__(self, value):
        self.value = value

    def interpret(self):
        return self.value


class AddExpression:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def interpret(self):
        return self.left.interpret() + self.right.interpret()


class SubtractExpression:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def interpret(self):
        return self.left.interpret() - self.right.interpret()


# 表示：10 + (5 - 2)
expression = AddExpression(
    NumberExpression(10),
    SubtractExpression(
        NumberExpression(5),
        NumberExpression(2),
    ),
)

print(expression.interpret())
```

### 怎么理解

Interpreter 的核心不是“写一个大 `if` 判断命令”，而是：**把语言里的不同规则表示成可以组合的对象。**

示例中：

```text
NumberExpression      → 一个数字规则
AddExpression         → 加法规则
SubtractExpression    → 减法规则
```

它们还能组合成：

```text
        Add
       /   \
     10   Subtract
          /    \
         5      2
```

每个节点只解释自己负责的规则，复杂表达式由这些小规则组合起来。

### 示例里省略了什么

真实系统往往还需要先把字符串：

```text
"ADD 10 SUB 5 2"
```

解析成 `AddExpression(...)`、`SubtractExpression(...)` 这样的表达式对象。

负责“把文本变成结构”的部分通常交给 Parser（解析器）。为了把注意力放在 Interpreter 本身，上面的示例直接从表达式对象开始，没有展开字符串解析。

### 实际开发提醒

现在很多解析问题会直接使用：

- Parser
- AST
- DSL 工具
- 编译器工具链

所以 GoF 风格 Interpreter 在普通业务代码里不算常见。

### 常见场景

- **搜索过滤表达式**：解释 `price > 100 AND category = "book"` 这类简单查询规则。
- **权限规则**：解释 `role == "admin" AND active` 这类可配置的访问条件。
- **工作流条件**：后台配置 `amount > 10000`、`country == "US"` 等简单规则，由程序解释执行。

### 常见误用

- 只是解析简单配置，却自己实现完整语法系统，维护成本过高。
- 语言已经比较复杂，仍手写大量 Interpreter 类，而不是使用成熟 Parser 工具。
- 没有清晰语法规则，只靠不断增加 `if/elif`，却把它称为 Interpreter。

普通业务开发里，这个模式更适合“认识思想”，而不是优先实践。

---

# 四、最容易混淆的模式

---

## Strategy vs State

两者代码结构非常相似。

### Strategy

关注：

> **我选择哪个算法？**

```python
order = Order(AlipayPayment())
```

例如：

```text
支付宝
微信
信用卡
```

### State

关注：

> **对象现在处于什么状态？**

```text
待支付
 ↓
已支付
 ↓
已发货
```

一句话：

```text
Strategy = 算法变化
State    = 状态变化
```

---

## Factory Method vs Abstract Factory

### Factory Method

通常创建：

> 一个产品

```python
factory.create()
```

### Abstract Factory

通常创建：

> 一族相关产品

```python
factory.create_button()
factory.create_checkbox()
```

记忆：

```text
Factory Method   → 一个产品
Abstract Factory → 一族产品
```

---

## Adapter vs Facade

### Adapter

问题：

> 接口不兼容。

```text
old.print_text()
        ↓
Adapter
        ↓
printer.print()
```

### Facade

问题：

> 接口太复杂。

```text
CPU + Memory + Disk
        ↓
      Facade
        ↓
computer.start()
```

记忆：

```text
Adapter = 转换接口
Facade  = 简化接口
```

---

## Decorator vs Proxy

结构都像：

```text
Wrapper
   ↓
RealObject
```

但目的不同：

```text
Decorator = 给对象增加能力
Proxy     = 控制对象访问
```

---

## Template Method vs Strategy

### Template Method

依靠：

> 继承

改变算法步骤。

### Strategy

依靠：

> 组合

替换算法。

```text
Template Method → 继承
Strategy        → 组合
```

这也是为什么现代设计中通常会强调：

> **组合优于继承。**

---

# 五、23 种模式速查表

| 分类   | 模式                    | 一句话理解                   |
| ------ | ----------------------- | ---------------------------- |
| 创建型 | Factory Method          | 让子类决定创建什么           |
| 创建型 | Abstract Factory        | 创建一整套相关对象           |
| 创建型 | Builder                 | 分步骤构建复杂对象           |
| 创建型 | Prototype               | 复制已有对象                 |
| 创建型 | Singleton               | 保证只有一个实例             |
| 结构型 | Adapter                 | 转换接口                     |
| 结构型 | Bridge                  | 分离两条独立变化轴           |
| 结构型 | Composite               | 单个对象和组合对象统一处理   |
| 结构型 | Decorator               | 动态增加功能                 |
| 结构型 | Facade                  | 给复杂系统提供简单入口       |
| 结构型 | Flyweight               | 共享大量重复对象             |
| 结构型 | Proxy                   | 控制对真实对象的访问         |
| 行为型 | Iterator                | 顺序访问集合                 |
| 行为型 | Template Method         | 固定骨架，部分步骤变化       |
| 行为型 | Strategy                | 替换算法                     |
| 行为型 | Visitor                 | 数据结构稳定，操作可扩展     |
| 行为型 | Chain of Responsibility | 请求沿处理链传递             |
| 行为型 | Mediator                | 通过中介协调对象             |
| 行为型 | Observer                | 一个变化，多个订阅者收到通知 |
| 行为型 | Memento                 | 保存和恢复状态               |
| 行为型 | State                   | 状态决定行为                 |
| 行为型 | Command                 | 把操作封装成对象             |
| 行为型 | Interpreter             | 解释简单语言                 |

---

# 六、从《好代码，坏代码》进入设计模式，建议这样学

不要按 23 个模式平均用力。

## 第一阶段：优先真正掌握 10 个

```text
Strategy
Factory Method
Builder
Adapter
Composite
Decorator
Facade
Proxy
Observer
State
```

这 10 个和实际代码设计的关系最直观。

重点观察：

- 哪里有很长的 `if / elif`
- 哪里直接依赖具体类
- 哪里接口不兼容
- 哪里调用方知道太多底层细节
- 哪里继承层次开始变复杂
- 哪里同一变化需要修改多个地方

---

## 第二阶段：理解更复杂的对象协作

```text
Template Method
Abstract Factory
Command
Chain of Responsibility
Mediator
```

这些模式更强调：

> 对象之间如何组织职责。

---

## 第三阶段：先做到“能识别”

```text
Prototype
Singleton
Bridge
Visitor
Memento
Flyweight
Interpreter
Iterator
```

它们不是不重要，而是：

- 有些 Python 已经提供语言级支持
- 有些使用场景较特殊
- 有些容易过度设计

---

# 七、看到什么坏味道，可以联想到什么模式？

这是最适合从《好代码，坏代码》进入设计模式的学习方式。

---

## 情况 1：巨大的 `if / elif`

例如：

```python
if payment == "alipay":
    ...
elif payment == "wechat":
    ...
elif payment == "credit_card":
    ...
```

先考虑：

```text
Strategy
```

如果判断的是对象生命周期状态：

```text
State
```

如果多个处理器依次尝试：

```text
Chain of Responsibility
```

---

## 情况 2：调用方直接创建大量具体类

例如：

```python
database = MySQLDatabase(...)
```

很多业务代码都知道 MySQL。

可以思考：

```text
Factory Method
Abstract Factory
```

目标不是“消灭 new / 构造函数”，而是：

> 避免高层业务被底层实现绑死。

---

## 情况 3：一个函数需要理解很多子系统

例如：

```python
cpu.start()
memory.load()
disk.mount()
network.connect()
service.start()
```

可以思考：

```text
Facade
```

让调用者只看到：

```python
system.start()
```

---

## 情况 4：继承组合开始爆炸

例如：

```text
Coffee
MilkCoffee
SugarCoffee
MilkSugarCoffee
CaramelMilkSugarCoffee
...
```

可以思考：

```text
Decorator
```

如果是两条独立变化维度：

```text
Bridge
```

---

## 情况 5：对象之间互相知道太多

例如：

```text
A 调 B
A 调 C
B 调 C
C 调 A
...
```

可以思考：

```text
Mediator
Observer
```

但要先问：

> 是否真的需要这些对象直接通信？

---

## 情况 6：代码需要 Undo / Redo

优先想到：

```text
Command
Memento
```

区别：

```text
Command → 保存“做了什么”
Memento → 保存“当时是什么状态”
```

---

# 八、设计模式学习中最重要的反模式：为了模式而模式

下面这种思路很危险：

> “我今天学了 Factory，所以我要在项目里找地方用 Factory。”

正确顺序应该是：

```text
发现具体设计问题
        ↓
分析变化与依赖
        ↓
寻找可选重构方案
        ↓
发现某个成熟方案恰好叫某种设计模式
```

而不是：

```text
先决定使用模式
        ↓
再找地方套进去
```

---

# 九、判断一个模式是否值得使用

每次准备引入设计模式时，可以问：

### 1. 当前真的存在变化吗？

如果没有变化需求，不要为未来幻想过度抽象。

### 2. 当前代码真的难理解吗？

如果：

```python
if condition:
    ...
else:
    ...
```

已经非常清楚，就不一定需要创建 5 个类。

### 3. 模式减少的复杂度，大于增加的复杂度吗？

这是最重要的判断。

例如把 10 行简单代码：

```text
变成
Interface
Factory
Strategy
Context
ConcreteStrategyA
ConcreteStrategyB
```

有可能只是把简单问题复杂化。

---

# 十、你真正应该形成的能力

学习 23 个模式最终不是为了做到：

> “我能默写 23 个 UML 图。”

而是看到代码时能判断：

```text
这里变化太多
这里耦合太强
这里调用者知道太多
这里职责混在一起
这里条件分支正在失控
这里继承已经不适合继续扩展
```

然后你脑中开始出现候选方案：

```text
Strategy?
Facade?
Adapter?
State?
Decorator?
Factory?
```

再选择：

> **最简单、最容易理解、足够解决当前问题的那个方案。**

这和《好代码，坏代码》的核心思想是连贯的。

---

# 十一、建议的实战练习顺序

建议不要只看代码。

每个模式都写一个 20～50 行的小练习。

## 练习 1：Strategy

把：

```python
if payment_type == ...
```

重构成支付策略。

---

## 练习 2：Factory Method

让业务代码不再直接创建：

```python
EmailSender()
SMSSender()
PushSender()
```

---

## 练习 3：Adapter

自己模拟：

```text
旧支付 SDK
新支付接口
```

然后写 Adapter。

---

## 练习 4：Facade

把一个需要 5 个步骤才能启动的子系统包装成：

```python
app.start()
```

---

## 练习 5：State

实现一个订单：

```text
Pending
Paid
Shipped
Cancelled
```

并让：

```python
order.process()
```

在不同状态下表现不同。

---

## 练习 6：Decorator

实现：

```text
基础日志
+ 时间
+ 用户 ID
+ Trace ID
```

不要通过 8 个子类组合，而是使用 Decorator。

---

## 练习 7：Observer

实现：

```text
OrderPaid
   ├── SendEmail
   ├── AddPoints
   └── UpdateInventory
```

体会事件解耦，同时观察调试难度是否上升。

---

# 十二、最后记住这句话

23 种设计模式表面上千差万别，但背后有一个非常统一的思想：

> **把会变化的东西，从相对稳定的东西中隔离出来。**

当这种隔离：

- 降低耦合
- 降低认知负担
- 让测试更容易
- 让修改更局部
- 让接口更清晰

设计模式才真正产生价值。

如果引入一个模式之后：

- 类更多了
- 跳转更多了
- 理解更困难了
- 修改并没有更安全

那么即使“形式上用了设计模式”，也不一定是好设计。
