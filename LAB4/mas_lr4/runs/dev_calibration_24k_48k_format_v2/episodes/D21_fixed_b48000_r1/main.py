def solve(data):
    done = set(data['done'])
    candidates = []
    for k, parents in data['deps'].items():
        if k in done:
            continue
        if all(p in done for p in parents):
            candidates.append(k)
    return sorted(candidates)
