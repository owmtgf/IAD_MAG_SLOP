def solve(data):
    left, right = data['day']
    out = []
    for a, b in sorted(data['intervals']):
        if a >= b:
            continue
        # Обрезаем интервал по [left, right)
        a = max(left, a)
        b = min(right, b)
        if a >= b:
            continue
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out
