def solve(data):
    done = set()
    out = []
    budget = data['budget']
    while True:
        ready = [k for k, parents in data['deps'].items() if k not in done and all(p in done for p in parents) and data['costs'][k] <= budget]
        if not ready:
            break
        node = max(ready, key=lambda k: (data['priority'][k], -ord(k[0]) if len(k) > 0 else 0))
        budget -= data['costs'][node]
        done.add(node)
        out.append(node)
    return {'order': out, 'remaining': budget}
