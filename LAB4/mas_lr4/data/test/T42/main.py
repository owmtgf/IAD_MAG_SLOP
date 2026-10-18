def solve(data):
    done = set()
    order = []
    while len(done) < len(data):
        ready = [k for k,parents in data.items() if k not in done and all(p in done for p in parents)]
        if not ready:
            return None
        node = max(ready)
        order.append(node)
        done.add(node)
    return order
