def solve(data):
    out = []
    for start, target in data['queries']:
        if start not in data['deps'] or target not in data['deps']:
            out.append(False)
            continue
        if start == target:
            out.append(True)
            continue
        seen = set()
        stack = list(data['deps'][start])
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            if node in data['deps']:
                stack.extend(data['deps'][node])
        out.append(target in seen)
    return out
