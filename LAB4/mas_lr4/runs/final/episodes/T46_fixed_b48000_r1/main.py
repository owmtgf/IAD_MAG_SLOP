def solve(data):
    affected = set(data['changed'])
    growing = True
    while growing:
        growing = False
        for node, parents in data['deps'].items():
            if node not in affected and any(p in affected for p in parents):
                affected.add(node)
                growing = True
    out = []
    done = set()
    while affected:
        candidates = [k for k in affected if k in data['deps'] and all(p in done for p in data['deps'][k])]
        if not candidates:
            break
        node = min(candidates)
        out.append(node)
        done.add(node)
        affected.remove(node)
    return out
