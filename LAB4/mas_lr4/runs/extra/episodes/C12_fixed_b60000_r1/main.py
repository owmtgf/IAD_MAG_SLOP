def path_matches(scope, resource):
    return resource.startswith(scope)


def active_at(record, moment):
    if moment < record["start"]:
        return False
    if record["end"] is not None and moment > record["end"]:
        return False
    return True


def matches(record, request):
    if not active_at(record, request["time"]):
        return False
    if record["action"] not in ["*", request["action"]]:
        return False
    return path_matches(record["resource"], request["resource"])


def direct_matches(policies, subject, request):
    result = []
    for policy in policies:
        if policy["subject"] in [subject, "*"] and matches(policy, request):
            result.append(policy.copy())
    return result


def inherited_matches(policies, delegations, request):
    actor = request["actor"]
    pending = [[actor, 0]]
    visited = {actor}
    inherited = []
    while pending:
        current, distance = pending.pop()
        if distance >= 3:
            continue
        for edge in delegations:
            sender = edge["from"]
            if edge["to"] != current or sender in visited:
                continue
            if not matches(edge, request):
                continue
            visited.add(sender)
            grants = direct_matches(policies, sender, request)
            for policy in grants:
                if policy["effect"] != "allow" or not policy["delegable"]:
                    continue
                forwarded = policy.copy()
                if len(edge["resource"]) > len(forwarded["resource"]):
                    forwarded["resource"] = edge["resource"]
                if edge["action"] != "*":
                    forwarded["action"] = edge["action"]
                inherited.append(forwarded)
            pending.append([sender, distance + 1])
    return inherited


def rank(policy):
    resource = policy["resource"]
    depth = 0 if resource == "/" else len(resource.split("/")) - 1
    action = 0 if policy["action"] == "*" else 1
    subject = 0 if policy["subject"] == "*" else 1
    return [action, depth, subject]


def decide(candidates):
    if not candidates:
        return {"decision": "deny", "sources": []}
    best = None
    winning = []
    for policy in candidates:
        priority = rank(policy)
        if best is None or priority > best:
            best = priority
            winning = [policy]
        elif priority == best:
            winning.append(policy)
    decision = "allow"
    sources = set()
    for policy in winning:
        sources.add(policy["id"])
        if policy["effect"] == "deny":
            decision = "deny"
    return {"decision": decision, "sources": sorted(sources)}


def solve(data):
    results = []
    for request in data["requests"]:
        candidates = direct_matches(data["policies"], request["actor"], request)
        candidates.extend(inherited_matches(data["policies"], data["delegations"], request))
        results.append(decide(candidates))
    return results
