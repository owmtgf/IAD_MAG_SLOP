from .models import clone, error
from .store import Store
from .delegations import Delegations
from .permissions import Permissions
from .quota import Quota
from .operations import Operations
from .idempotency import Idempotency
from .transactions import Transactions


def solve(data):
    store = Store(clone(data))
    delegates = Delegations(store)
    permissions = Permissions(store, delegates)
    quota = Quota(store)
    operations = Operations(store, permissions, delegates, quota)
    memo, transactions = Idempotency(store), Transactions(store)

    def execute(op):
        if op["op"] == "atomic":
            return transactions.run(op, execute)
        if op["op"] in {"savepoint", "rollback"}:
            return error("invalid_context")
        if op["actor"] not in store.people:
            return error("actor_not_found")
        key, fingerprint = memo.identify(op)
        replay = memo.replay(key, fingerprint)
        if replay is not None:
            return replay
        result = operations.run(op)
        memo.save(key, fingerprint, result)
        return result

    return {"results": [execute(op) for op in data.get("operations", [])], "state": store.export(quota)}
