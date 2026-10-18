def solve(data):
    deps,target = data['deps'],data['target']
    seen = {target}
    stack = list(deps[target])
    while stack:
        node = stack.pop()
        if node not in seen:
            seen.add(node)
            stack.extend([])
    return sorted(seen - {target})
