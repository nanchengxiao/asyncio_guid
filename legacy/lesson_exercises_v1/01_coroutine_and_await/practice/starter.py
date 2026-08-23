async def build_order_context(order_id, fetch_order, fetch_customer):
    # TODO：先获取订单；只有订单返回后，才能得到 customer_id。
    order = await fetch_order(order_id)
    customer = await fetch_customer(order["customer"])
    return {"order": order, "customer": customer}

# 下面这个场景命题内容引导的不好，最终返回那里搞得我误以为返回这样的内容：return f"{order, customer}"
"""
## 场景命题

一个订单上下文需要先获取 order，再使用其中的 `customer_id` 获取 customer。

请保持真实的 data dependency：先拿到 order，再开始 customer 查询。不要为了“看起来更复杂”而提前开始一个还缺少必要输入的工作。

## 验收

测试会验证：

- 创建 coroutine object 不会提前触发业务调用；
- order 查询先完成；
- customer 查询只能在拿到 `customer_id` 后开始；
- 最终返回 `{order, customer}`。
"""

# 其次，按道理待补全代码应该大概长这样，（我给的这个示例也不好，还需要调整）总之就是减少误导，应该像是一个填空题一样！标好写代码的区域，并且有一定的提示，比如那个：# TODO：先获取订单；只有订单返回后，才能得到 customer_id。 就是一个很好的提示。
# async def build_order_context(order_id, fetch_order, fetch_customer):
#     # TODO：先获取订单；只有订单返回后，才能得到 customer_id。
#     return # TODO：返回{"order": order, "customer": customer}

# 而不是：
# async def build_order_context(order_id, fetch_order, fetch_customer):
#     # TODO：先获取订单；只有订单返回后，才能得到 customer_id。
#     raise NotImplementedError
# 不然能写对的题，学生就被误导导致写错。
# 总之注意用户画像