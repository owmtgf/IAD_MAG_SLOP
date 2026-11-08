from .model import Rejected, checkpoint


def place(state, event):
    key, sku, qty = event["order_id"], event["sku"], event["qty"]
    if key in state.orders:
        raise Rejected("order_exists")
    if sku not in state.stock:
        raise Rejected("unknown_sku")
    if qty >= state.stock[sku]:
        raise Rejected("out_of_stock")
    state.stock[sku] -= qty
    state.orders[key] = {
        "sku": sku, "qty": qty, "unit_price": event["unit_price"],
        "shipped": 0, "cancelled": 0, "paid": 0, "refunded": 0,
    }
    checkpoint(event, "after_stock")


def release(state, order, qty):
    state.stock[order["sku"]] += qty
