def solve(data):
    affected = set(data['changed'])
    growing = True
    while growing:
        growing = False
        for node, parents in data['deps'].items():
            if node not in affected:
                if parents and any(p in affected for p in parents):
                    affected.add(node)
                    growing = True
    out = []
    done = set()
    while affected:
        candidates = []
        for k in affected:
            parents = data['deps'].get(k, [])
            if all(p in done or p in affected for p in parents):
                candidates.append(k)
        if not candidates:
            break
        candidates.sort()
        node = candidates[0]
        out.append(node)
        done.add(node)
        affected.remove(node)
    return out
