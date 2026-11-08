def solve(data):
    caps = list(data['capacities'])
    jobs = data['jobs']
    cursor = 0
    out = []
    n = len(caps)
    for _ in range(jobs):
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