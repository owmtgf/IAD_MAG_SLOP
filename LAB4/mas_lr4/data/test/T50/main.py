def solve(data):
    out = []
    for start,target in data['queries']:
        if start not in data['deps'] or target not in data['deps']:
            out.append(False)
            continue
        seen = set()
        stack = list(data['deps'][start])
        while stack:
            node = stack.pop()
            if node not in seen:
                seen.add(node)
                stack.extend([])
        out.append(target in seen)
    return out
