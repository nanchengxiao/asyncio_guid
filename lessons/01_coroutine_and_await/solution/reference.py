async def build_order_context(order_id, fetch_order, fetch_customer):
    order = await fetch_order(order_id)
    customer = await fetch_customer(order["customer_id"])
    return {"order": order, "customer": customer}
