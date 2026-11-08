from .models import clone, document, dto, error
from .versions import record


class Operations:
    def __init__(self, store, permissions, delegations, quota):
        self.store, self.permissions = store, permissions
        self.delegations, self.quota = delegations, quota

    def run(self, op):
        kind, actor = op["op"], op["actor"]
        if kind == "create":
            if op["id"] in self.store.state["docs"]:
                return error("document_exists")
            tenant = self.store.people[actor]
            if not self.quota.fits(tenant, op["text"]):
                return error("quota_exceeded")
            doc = document(op["id"], tenant, actor, op["text"])
            self.store.state["docs"][op["id"]] = doc
            self.store.invalidate()
            return dto(doc)
        doc = self.store.find(actor, op["id"])
        if doc is None:
            return error("document_not_found")
        required = {"read": "read", "write": "write", "delete": "write",
                    "acl": "share", "delegate": "share", "revoke": "share"}[kind]
        if required not in self.permissions.effective(actor, doc):
            return error("permission_denied")
        if kind == "read":
            return dto(doc, op.get("version"))
        if kind in {"write", "delete"}:
            if op["expected"] != doc["version"]:
                return error("version_conflict", actual=doc["version"])
            if kind == "write":
                if not self.quota.fits(doc["tenant"], op["text"], doc["text"]):
                    return error("quota_exceeded")
                record(doc, op["text"])
                return dto(doc)
            record(doc, None)
            doc["deleted"] = True
            self.store.invalidate()
            return {"id": doc["id"], "deleted": True, "version": doc["version"]}
        if kind in {"acl", "delegate"}:
            recipient = op["principal"] if kind == "acl" else op["recipient"]
            if recipient not in self.store.people:
                return error("principal_not_found")
            if self.store.people[recipient] != doc["tenant"]:
                return error("tenant_mismatch")
        if kind == "acl":
            doc["acl"][op["principal"]] = {"allow": sorted(op.get("allow", [])), "deny": sorted(op.get("deny", []))}
            return {"id": doc["id"], "principal": op["principal"], **clone(doc["acl"][op["principal"]])}
        if kind == "delegate":
            gid = op["grant"]
            if gid in self.store.state["grants"]:
                return error("grant_exists")
            parent = op.get("via")
            if parent is None:
                source = self.permissions.direct(actor, doc)
            else:
                grant = self.store.state["grants"].get(parent)
                if grant is None or grant["doc"] != doc["id"] or grant["recipient"] != actor or not self.delegations.active(parent):
                    return error("invalid_parent")
                source = set(grant["rights"]) & self.permissions.effective(actor, doc)
            if "share" not in source or not set(op["rights"]) <= source:
                return error("permission_denied")
            self.delegations.insert(gid, doc["id"], actor, op["recipient"], op["rights"], parent)
            return {"grant": gid, "revoked": False}
        grant = self.store.state["grants"].get(op["grant"])
        if grant is None or grant["doc"] != doc["id"]:
            return error("grant_not_found")
        self.delegations.revoke(grant)
        return {"grant": grant["id"], "revoked": True}
