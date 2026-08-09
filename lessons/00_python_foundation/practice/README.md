# Practice — managed record stream

## 业务背景
报表导入器从一个必须显式关闭的数据源逐条读取记录。调用方可能只读取前几条就停止。

## 输入 / 输出
输入 iterable 与 `close_resource()` 回调；输出一个 context manager，进入后得到惰性 iterator。

## 约束
- 不得把输入一次性转成 list。
- 无论正常结束、consumer 提前退出还是异常，退出 context 时都调用一次 cleanup。

## TODO
实现资源生命周期与惰性迭代。

## 验收
`uv run pytest lessons/00_python_foundation/tests -v --learner`
