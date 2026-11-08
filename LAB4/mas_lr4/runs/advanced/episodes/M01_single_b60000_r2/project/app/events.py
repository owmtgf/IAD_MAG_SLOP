from .inventory import place
from .payments import pay
from .shipping import ship
from .cancellation import cancel
from .refunds import refund

HANDLERS = {"place": place, "pay": pay, "ship": ship, "cancel": cancel, "refund": refund}


def dispatch(state, event):
    HANDLERS[event["type"]](state, event)
