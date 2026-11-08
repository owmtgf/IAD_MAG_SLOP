def solve(data):
    left, right = data['day']
    intervals = data['intervals']
    out = []
    for a, b in sorted(intervals):
        a = max(a, left)
        b = min(b, right)
        if a >= b:
            continue
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out