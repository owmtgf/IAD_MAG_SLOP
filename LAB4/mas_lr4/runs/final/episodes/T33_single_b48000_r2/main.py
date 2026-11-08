def solve(data):
    caps = list(data['capacities'])
    jobs = data['jobs']
    out = []
    cursor = 0
    n = len(caps)
    if n == 0:
        return [None] * jobs
    for _ in range(jobs):
        found = None
        for shift in range(n):
            i = (cursor + shift) % n
            if caps[i] > 0:
                found = i
                caps[i] -= 1
                cursor = (i + 1) % n
                break
        if found is None:
            out.append(None)
        else:
            out.append(found)
    return out