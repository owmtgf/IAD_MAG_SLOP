def solve(data):
    done = set(data['done'])
    result = []
    for k, parents in data['deps'].items():
        if k in done:
            continue
        if all(p in done for p in parents):
            result.append(k)
    return sorted(result)
