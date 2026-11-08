import copy

RIGHTS = {"read", "write", "share"}


def error(code, **fields):
    return {"error": code, **fields}


def document(doc_id, tenant, owner, text, acl=()):
    return {"id": doc_id, "tenant": tenant, "owner": owner, "text": text,
            "version": 1, "deleted": False, "history": [{"version": 1, "text": text}],
            "acl": {a["principal"]: {"allow": sorted(a.get("allow", [])), "deny": sorted(a.get("deny", []))} for a in acl}}


def dto(doc, version=None):
    v = doc["version"] if version is None else version
    entry = next((x for x in doc["history"] if x["version"] == v), None)
    if entry is None:
        return error("version_not_found")
    return {"id": doc["id"], "owner": doc["owner"], "text": entry["text"], "version": v}


def clone(value):
    return copy.deepcopy(value)
