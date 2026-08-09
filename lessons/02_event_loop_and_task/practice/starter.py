async def build_dashboard(user_id, fetch_user, fetch_orders):
    # TODO：user 与 orders 彼此无数据依赖，应让两段 I/O 等待尽可能重叠。
    raise NotImplementedError
