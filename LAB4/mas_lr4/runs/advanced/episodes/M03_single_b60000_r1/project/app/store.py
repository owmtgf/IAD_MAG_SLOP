from .models import clone, document


class Store:
    def __init__(self, data):
        self.tenants = {t["id"]: t["quota"] for t in data["tenants"]}
        self.people = {p["id"]: p["tenant"] for p in data["principals"]}
        self.state = {"docs": {}, "grants": {}, "memo": {}, "cache": {}}
        for d in data.get("documents", []):
            self.state["docs"][d["id"]] = document(d["id"], d["tenant"], d["owner"], d["text"], d.get("acl", []))

    def find(self, actor, doc_id):
        doc = self.state["docs"].get(doc_id)
        if doc is None or doc["deleted"]:
            return None
        return doc

    def invalidate(self):
        self.state["cache"].clear()

    def export(self, quota):
        docs = []
        for doc_id in sorted(self.state["docs"]):
            d = self.state["docs"][doc_id]
            item = {k: clone(d[k]) for k in ("id", "tenant", "owner", "text", "version", "deleted", "history")}
            item["acl"] = [{"principal": p, **clone(d["acl"][p])} for p in sorted(d["acl"])]
            docs.append(item)
        return {"documents": docs, "grants": [clone(self.state["grants"][g]) for g in sorted(self.state["grants"])],
                "usage": {t: quota.usage(t) for t in sorted(self.tenants)}}
