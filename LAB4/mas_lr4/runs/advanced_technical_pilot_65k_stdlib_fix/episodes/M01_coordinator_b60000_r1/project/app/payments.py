from .model import Rejected, checkpoint, order_for


def record(state, event, kind, amount, source):
    state.ledger.append({"event_id": event["id"], "order_id": event["order_id"],
                         "kind": kind, "amount": amount, "source": source})


def pay(state, event):
    order = order_for(state, event)
    active = order["qty"] - order["cancelled"]
    if active == 0:
        raise Rejected("inactive_order")
    if order["paid"] + event["amount"] > active * order["unit_price"]:
        raise Rejected("overpayment")
    order["paid"] += event["amount"]
    record(state, event, "payment", event["amount"], "pay")
    checkpoint(event, "after_ledger")
