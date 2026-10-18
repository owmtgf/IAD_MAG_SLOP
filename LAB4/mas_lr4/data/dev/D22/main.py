def solve(data):
    deps,order = data['deps'],data['order']
    if not set(order).issubset(set(deps)):
        return False
    seen = set()
    for name in order:
        if not all(p in seen for p in deps[name]):
            return False
        seen.add(name)
    return True
