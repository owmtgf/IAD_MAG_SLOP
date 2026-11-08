"""Public entrypoint. No globals survive a call to solve."""
from .model import State, Rejected, InjectedFailure, remaining, net
from .events import dispatch
from .transaction import atomic
from .idempotency import is_duplicate, finish


def solve(data):
    state = State(stock=dict(data["stock"]))
    results = []
    for event in data["events"]:
        result = {"event_id": event["id"]}
        if is_duplicate(state, event):
            result["status"] = "duplicate"
        else:
            try:
                with atomic(state):
                    dispatch(state, event)
                result["status"] = "applied"
            except Rejected as exc:
                result.update(status="rejected", reason=str(exc))
            except InjectedFailure:
                result.update(status="failed", reason="injected_failure")
            finish(state, event, result["status"])
        results.append(result)
    orders = {}
    for key in sorted(state.orders):
        order = state.orders[key]
        orders[key] = dict(order, reserved=remaining(order), net_paid=net(order))
    return {"stock": dict(sorted(state.stock.items())), "orders": orders,
            "ledger": state.ledger, "shipments": state.shipments, "results": results}
