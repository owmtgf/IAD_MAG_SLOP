from .model import Rejected, checkpoint, order_for, remaining
from .inventory import release


def ship(state, event):
    order = order_for(state, event)
    qty = event["qty"]
    if qty > remaining(order):
        raise Rejected("quantity_exceeded")
    if order["paid"] < (order["shipped"] + qty) * order["unit_price"]:
        raise Rejected("not_paid")
    order["shipped"] += qty
    release(state, order, qty)
    state.shipments.append({"event_id": event["id"], "order_id": event["order_id"], "qty": qty})
    checkpoint(event, "after_shipping")
