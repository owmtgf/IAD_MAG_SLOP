from dataclasses import dataclass, field


class Rejected(Exception):
    pass


class InjectedFailure(Exception):
    pass


def checkpoint(event, name):
    if event.get("fail_at") == name:
        raise InjectedFailure(name)


@dataclass
class State:
    stock: dict
    orders: dict = field(default_factory=dict)
    ledger: list = field(default_factory=list)
    shipments: list = field(default_factory=list)
    seen: set = field(default_factory=set)


def order_for(state, event):
    try:
        return state.orders[event["order_id"]]
    except KeyError:
        raise Rejected("unknown_order") from None


def remaining(order):
    return order["qty"] - order["shipped"] - order["cancelled"]


def net(order):
    return order["paid"] - order["refunded"]
