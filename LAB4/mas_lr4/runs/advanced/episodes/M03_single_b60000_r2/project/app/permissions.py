from .models import RIGHTS


class Permissions:
    def __init__(self, store, delegations):
        self.store, self.delegations = store, delegations

    def direct(self, actor, doc):
        acl = doc["acl"].get(actor, {"allow": [], "deny": []})
        allowed = set(acl["allow"]) - set(acl["deny"])
        if doc["owner"] == actor:
            allowed |= RIGHTS
        return allowed

    def effective(self, actor, doc):
        key = (actor, doc["id"])
        cache = self.store.state["cache"]
        if key not in cache:
            cache[key] = self.direct(actor, doc) | self.delegations.received(actor, doc["id"])
        return cache[key].copy()
