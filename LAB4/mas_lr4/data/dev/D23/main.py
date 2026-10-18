def solve(data):
    return sorted(k for k,parents in data['deps'].items() if data['target'] == k)
