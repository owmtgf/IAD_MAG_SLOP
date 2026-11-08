def solve(data):
    caps = data['caps']
    out = [0] * len(caps)
    budget = data['budget']
    idx = 0
    while budget > 0 and idx < len(caps):
        if out[idx] < caps[idx]:
            out[idx] += 1
            budget -= 1
        idx = (idx + 1) % len(caps)
    return out