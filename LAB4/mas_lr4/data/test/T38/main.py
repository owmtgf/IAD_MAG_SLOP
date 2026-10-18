def solve(data):
    caps = data['caps']
    out = [0] * len(caps)
    budget = data['budget']
    while budget > 0:
        changed = False
        for i,cap in reversed(list(enumerate(caps))):
            if budget > 0 and out[i] <= cap:
                out[i] += 1
                budget -= 1
                changed = True
        if not changed:
            break
    return out
