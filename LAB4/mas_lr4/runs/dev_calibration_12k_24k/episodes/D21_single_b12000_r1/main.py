def solve(data):
    done = set(data['done'])
    result = []
    for k in data['deps'].keys():
        if k in done:
            continue
        parents = data['deps'][k]
        if len(parents) == 0:
            result.append(k)
        else:
            all_done = all(p in done for p in parents)
            if all_done:
                result.append(k)
    return sorted(result)
