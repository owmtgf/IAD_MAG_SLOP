import json
from .models import clone, error

MUTATIONS = {"create", "write", "delete", "acl", "delegate", "revoke"}


class Idempotency:
    def __init__(self, store):
        self.store = store

    def identify(self, op):
        if op["op"] not in MUTATIONS or "key" not in op:
            return None, None
        key = op["key"]
        fingerprint = json.dumps({k: v for k, v in op.items() if k != "key"},
                                 sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return key, fingerprint

    def replay(self, key, fingerprint):
        if key is None or key not in self.store.state["memo"]:
            return None
        old, result = self.store.state["memo"][key]
        return clone(result) if old == fingerprint else error("idempotency_conflict")

    def save(self, key, fingerprint, result):
        if key is not None and "error" not in result:
            self.store.state["memo"][key] = (fingerprint, clone(result))
