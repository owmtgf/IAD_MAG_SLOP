from .model import Rejected, checkpoint, order_for, remaining, net
from .inventory import release
from .refunds import credit


def cancel(state, event):
    order = order_for(state, event)
    qty = event["qty"]
    if qty > remaining(order):
        raise Rejected("quantity_exceeded")
    order["cancelled"] += qty
    release(state, order, qty)
    checkpoint(event, "after_stock")
    surplus = max(0, net(order) - order["qty"] * order["unit_price"])
    credit(state, order, event, surplus, "cancel")
    checkpoint(event, "after_refund")
