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
    original_paid = order["paid"]
    original_refunded = order["refunded"]
    original_qty = order["qty"]
    original_cancelled = order["cancelled"]
    new_cancelled = order["cancelled"]
    new_net_paid = net(order)
    amount_to_refund = max(0, original_paid - new_net_paid)
    if amount_to_refund > 0:
        credit(state, order, event, amount_to_refund, "cancel")
    checkpoint(event, "after_refund")