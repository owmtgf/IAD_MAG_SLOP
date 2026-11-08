from .model import Rejected, checkpoint, order_for, net
from .payments import record


def credit(state, order, event, amount, source):
    if amount:
        order["refunded"] += amount
        record(state, event, "refund", amount, source)


def refund(state, event):
    order = order_for(state, event)
    amount = event["amount"]
    if amount > net(order):
        raise Rejected("refund_exceeded")
    credit(state, order, event, amount, "refund")
    checkpoint(event, "after_ledger")
