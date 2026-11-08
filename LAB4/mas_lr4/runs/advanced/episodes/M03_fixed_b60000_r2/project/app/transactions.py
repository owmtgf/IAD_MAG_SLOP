from .models import clone, error


class Transactions:
    def __init__(self, store):
        self.store = store

    def run(self, op, execute):
        before = clone(self.store.state)
        points, order, results = {}, [], []
        for index, child in enumerate(op["operations"]):
            if child["op"] == "savepoint":
                name = child["name"]
                points[name] = self.store.state.copy()
                order.append(name)
                result = {"savepoint": name}
            elif child["op"] == "rollback":
                name = child["name"]
                if name not in points:
                    result = error("savepoint_not_found")
                else:
                    self.store.state = clone(points[name])
                    for later in order[order.index(name) + 1:]:
                        del points[later]
                    order = order[:order.index(name) + 1]
                    result = {"rolled_back": name}
            else:
                result = execute(child)
            if "error" in result:
                self.store.state = before
                return error("transaction_failed", index=index, cause=result, results=results)
            results.append(result)
        return {"ok": True, "results": results}
