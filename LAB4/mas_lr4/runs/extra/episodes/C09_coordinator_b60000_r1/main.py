def build_orders(items):
    orders = {}
    for item in items:
        orders[item["id"]] = {
            "total": item["total"],
            "paid": 0,
            "refunded": 0,
            "state": "open"
        }
    return orders


def event_key(event):
    return [event["order"], event["op"]]


def apply_payment(order, amount):
    if order["state"] != "open":
        return False
    if amount <= 0:
        return False
    if order["paid"] + amount > order["total"]:
        return False
    order["paid"] += amount
    return True


def apply_refund(order, amount):
    if order["state"] not in ["shipped", "cancelled"]:
        return False
    if amount <= 0 or amount > order["paid"]:
        return False
    order["refunded"] += amount
    return True


def apply_event(order, event):
    op = event["op"]
    if op == "pay":
        return apply_payment(order, event["amount"])
    if op == "refund":
        return apply_refund(order, event["amount"])
    if op == "ship":
        if order["state"] != "open":
            return False
        if order["paid"] != order["total"]:
            return False
        order["state"] = "shipped"
        return True
    if op == "cancel":
        if order["state"] == "shipped":
            return False
        order["state"] = "cancelled"
        order["paid"] = 0
        return True
    return False


def output_order(oid, order):
    due = max(0, order["total"] - order["paid"])
    if order["state"] == "cancelled":
        due = 0
    return {
        "id": oid,
        "state": order["state"],
        "paid": order["paid"],
        "refunded": order["refunded"],
        "net": order["paid"] - order["refunded"],
        "due": due
    }


def solve(data):
    orders = build_orders(data["orders"])
    seen = {}
    log = []
    for event in data["events"]:
        oid = event["order"]
        eid = event["id"]
        cache_key = [oid, eid]
        cached = seen.get(tuple(cache_key))
        signature = event_key(event)
        if cached is not None:
            matches = cached == signature
            log.append({
                "id": eid,
                "status": "applied" if matches else "conflict",
                "replay": matches
            })
            continue
        order = orders.get(oid)
        applied = False
        if order is not None:
            applied = apply_event(order, event)
        status = "applied" if applied else "rejected"
        if applied:
            seen[tuple(cache_key)] = signature
        log.append({"id": eid, "status": status, "replay": False})
    result = []
    for oid in sorted(orders):
        result.append(output_order(oid, orders[oid]))
    return {"orders": result, "log": log}
