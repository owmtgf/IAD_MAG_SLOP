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
    original_qty = order["qty"]
    original_cancelled = order["cancelled"]
    original_net = net(order)
    new_cancelled = order["cancelled"]
    new_net = original_net - (original_qty - new_cancelled) * order["unit_price"]
    if new_net > 0:
        credit(state, order, event, new_net, "cancel")
    checkpoint(event, "after_refund")
