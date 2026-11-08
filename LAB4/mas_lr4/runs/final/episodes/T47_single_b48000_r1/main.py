def solve(data):
    done = set()
    out = []
    budget = data['budget']
    while True:
        ready = []
        for k, parents in data['deps'].items():
            if k not in done and all(p in done for p in parents) and data['costs'][k] <= budget:
                ready.append(k)
        if not ready:
            break
        node = max(ready, key=lambda k: (data['priority'][k], k))
        budget -= data['costs'][node]
        done.add(node)
        out.append(node)
    return {'order': out, 'remaining': budget}
