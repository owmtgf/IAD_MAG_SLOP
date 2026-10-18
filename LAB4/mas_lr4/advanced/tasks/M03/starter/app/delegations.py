class Delegations:
    def __init__(self, store):
        self.store = store

    def active(self, grant_id):
        grant = self.store.state["grants"][grant_id]
        return not grant["revoked"]

    def received(self, actor, doc_id):
        rights = set()
        for gid, grant in self.store.state["grants"].items():
            if grant["doc"] == doc_id and grant["recipient"] == actor and self.active(gid):
                rights.update(grant["rights"])
        return rights

    def insert(self, gid, doc_id, actor, recipient, rights, parent):
        self.store.state["grants"][gid] = {"id": gid, "doc": doc_id, "issuer": actor,
            "recipient": recipient, "rights": sorted(rights), "parent": parent, "revoked": False}
        self.store.invalidate()

    def revoke(self, grant):
        grant["revoked"] = True
        self.store.invalidate()
