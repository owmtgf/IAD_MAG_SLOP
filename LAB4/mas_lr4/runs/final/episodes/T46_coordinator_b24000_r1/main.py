def solve(data):
    affected = set(data.get('changed', []))
    growing = True
    while growing:
        growing = False
        for node, parents in data.get('deps', {}).items():
            if node not in affected and any(p in affected for p in parents):
                affected.add(node)
                growing = True
    out = []
    done = set()
    while affected:
        candidates = [k for k in affected if all(p in done for p in data.get('deps', {}).get(k, []))]
        if not candidates:
            break
        node = min(candidates)
        out.append(node)
        done.add(node)
        affected.remove(node)
    return out
