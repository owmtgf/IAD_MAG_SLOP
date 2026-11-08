def solve(data):
    caps = data['caps']
    out = [0] * len(caps)
    budget = data['budget']
    n = len(caps)
    idx = 0
    while budget > 0 and idx < n:
        if out[idx] < caps[idx]:
            out[idx] += 1
            budget -= 1
        idx = (idx + 1) % n
    return out
