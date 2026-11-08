def solve(data):
    caps = data['caps']
    out = [0] * len(caps)
    budget = data['budget']
    n = len(caps)
    if n == 0:
        return []
    idx = 0
    while budget > 0:
        if out[idx] < caps[idx]:
            out[idx] += 1
            budget -= 1
        else:
            idx = (idx + 1) % n
        if idx == 0 and out[0] >= caps[0]:
            break
    return out
