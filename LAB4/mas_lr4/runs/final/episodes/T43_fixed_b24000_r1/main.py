def solve(data):
    finished = {}
    while len(finished) < len(data['deps']):
        ready = [k for k, parents in data['deps'].items() if k not in finished and all(p in finished for p in parents)]
        if not ready:
            return None
        for node in ready:
            preds = data['deps'][node]
            if not preds:
                start = 0
            else:
                start = max(finished[p] for p in preds)
            finished[node] = start + data['durations'][node]
    return finished
