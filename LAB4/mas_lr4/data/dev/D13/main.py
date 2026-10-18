def solve(data):
    seen = set()
    out = []
    for value in data:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return sorted(out)
