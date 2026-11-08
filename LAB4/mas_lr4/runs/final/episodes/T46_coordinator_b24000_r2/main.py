def solve(data):
    affected = set(data['changed'])
    growing = True
    while growing:
        growing = False
        for node, parents in data['deps'].items():
            if node not in affected:
                for p in parents:
                    if p in affected:
                        affected.add(node)
                        growing = True
                        break
    out = []
    done = set()
    while affected:
        candidates = []
        for k in affected:
            if all(p in done for p in data['deps'].get(k, [])):
                candidates.append(k)
        if not candidates:
            break
        candidates.sort()
        node = candidates[0]
        out.append(node)
        done.add(node)
        affected.remove(node)
    return out
