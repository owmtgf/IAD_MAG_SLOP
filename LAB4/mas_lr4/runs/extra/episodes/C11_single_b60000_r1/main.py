def clone_rows(rows):
    return {key: row.copy() for key, row in rows.items()}


def sorted_rows(rows):
    return [rows[key].copy() for key in sorted(rows)]


def valid_rows(rows, total):
    slots = set()
    amount = 0
    for key, row in rows.items():
        if row["amount"] < 0:
            return False
        amount += row["amount"]
        if row["slot"] in slots:
            return False
        slots.add(row["slot"])
        parent = row["parent"]
        if parent is not None:
            if parent not in rows or parent == key:
                return False
    return amount <= total


def locate_savepoint(savepoints, name):
    for index, point in enumerate(savepoints):
        if point[0] == name:
            return index
    return None


def solve(data):
    committed = {row["id"]: row.copy() for row in data["rows"]}
    active = False
    working = {}
    savepoints = []
    log = []
    for command in data["commands"]:
        op = command["op"]
        status = "rejected"
        if op == "begin":
            if not active:
                active = True
                working = clone_rows(committed)
                savepoints = []
                status = "ok"
        elif not active:
            log.append(status)
            continue
        elif op == "put":
            row = command["row"]
            if row["amount"] >= 0:
                working[row["id"]] = row.copy()
                status = "ok"
        elif op == "delete":
            key = command["id"]
            if key in working:
                working.pop(key)
                status = "ok"
        elif op == "savepoint":
            point = [command["name"], clone_rows(working)]
            index = locate_savepoint(savepoints, command["name"])
            if index is None:
                savepoints.append(point)
            else:
                savepoints[index] = point
            status = "ok"
        elif op == "rollback_to":
            index = locate_savepoint(savepoints, command["name"])
            if index is not None:
                working = clone_rows(savepoints[index][1])
                savepoints = savepoints[:index]
                status = "ok"
        elif op == "release":
            index = locate_savepoint(savepoints, command["name"])
            if index is not None:
                savepoints.pop(index)
                status = "ok"
        elif op == "commit":
            valid = valid_rows(working, data["total"])
            if valid:
                committed = clone_rows(working)
                status = "ok"
            else:
                status = "constraint"
            active = False
            working = {}
            savepoints = []
        elif op == "abort":
            active = False
            working = {}
            savepoints = []
            status = "ok"
        log.append(status)
    result = {
        "rows": sorted_rows(committed),
        "pending": None,
        "savepoints": [point[0] for point in savepoints],
        "log": log
    }
    if active:
        result["pending"] = sorted_rows(working)
    return result
