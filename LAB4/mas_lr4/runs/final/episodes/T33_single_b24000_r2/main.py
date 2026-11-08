def solve(data):
    caps = list(data['capacities'])
    n = len(caps)
    if n == 0:
        return [None] * data['jobs']
    cursor = 0
    out = []
    for _ in range(data['jobs']):
        found = None
        for shift in range(n):
            i = (cursor + shift) % n
            if caps[i] > 0:
                found = i
                caps[i] -= 1
                cursor = (i + 1) % n
                break
        if found is not None:
            out.append(found)
        else:
            out.append(None)
    return out