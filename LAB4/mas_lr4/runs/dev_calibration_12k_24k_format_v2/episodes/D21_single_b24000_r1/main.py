def solve(data):
    done = set(data['done'])
    result = []
    for k in data['deps'].keys():
        if k in done:
            continue
        parents = data['deps'][k]
        if all(p in done for p in parents):
            result.append(k)
    return sorted(result)
