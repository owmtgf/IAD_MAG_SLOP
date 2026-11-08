def solve(data):
    left, right = data['day']
    if left >= right:
        return []
    out = []
    for a, b in sorted(data['intervals']):
        a = max(a, left)
        b = min(b, right)
        if a >= b:
            continue
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out