# Practice — managed record stream

## 业务背景

报表导入器从一个必须显式关闭的数据源逐条读取记录。调用方可能只读取前几条就停止。

## 输入 / 输出

输入：

- `records`：一批可以逐个读取的记录；
- `close_resource()`：关闭底层资源的回调函数。

输出：一个 context manager。进入 `with` 后，调用者可以逐条取得记录。

这里要求记录采用**按需产生**的方式：调用者要下一条时才取下一条，不要一开始就把所有输入都复制到列表里。这种“需要一个才产生一个”的方式也叫**惰性（lazy）处理**。

## 约束

- 不得把输入一次性转成 `list`。
- 记录要保持原来的顺序。
- 无论正常结束、调用者提前停止还是发生异常，退出 `with` 时都调用一次 `close_resource()`。

## TODO

实现“逐条按需读取 + 离开 `with` 时可靠清理资源”。

## 验收

```bash
uv run pytest lessons/00_python_foundation/tests -v --learner
```
