def solve(data):
    caps = data['caps']
    out = [0] * len(caps)
    budget = data['budget']
    n = len(caps)
    if n == 0:
        return []
    
    while budget > 0:
        changed = False
        for i in range(n):
            if out[i] < caps[i]:
                out[i] += 1
                budget -= 1
                changed = True
        if not changed:
            break
    return out
