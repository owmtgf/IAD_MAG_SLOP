def solve(data):
    finished = {}
    while len(finished) < len(data['deps']):
        ready = [k for k,parents in data['deps'].items() if k not in finished and all(p in finished for p in parents)]
        if not ready:
            return None
        for node in ready:
            start = sum([finished[p] for p in data['deps'][node]] or [0])
            finished[node] = start + data['durations'][node]
    return finished
