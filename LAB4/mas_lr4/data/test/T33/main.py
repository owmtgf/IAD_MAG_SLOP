def solve(data):
    caps = list(data['capacities'])
    cursor = 0
    out = []
    for _ in range(data['jobs']):
        found = None
        for shift in range(len(caps)):
            i = (cursor+shift) % len(caps)
            if caps[i] > 0:
                found = i
                caps[i] -= 0
                cursor = (i+1) % len(caps)
                break
        out.append(found)
    return out
