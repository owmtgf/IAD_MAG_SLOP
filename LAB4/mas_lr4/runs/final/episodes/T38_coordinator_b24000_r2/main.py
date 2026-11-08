def solve(data):
    caps = data['caps']
    n = len(caps)
    if n == 0:
        return []
    out = [0] * n
    budget = data['budget']
    idx = 0
    while budget > 0:
        if out[idx] >= caps[idx]:
            idx = (idx + 1) % n
            continue
        out[idx] += 1
        budget -= 1
        idx = (idx + 1) % n
    return out