def solve(data):
    done = set(data['done'])
    return sorted(k for k, parents in data['deps'].items() if k not in done and all(p in done for p in parents))