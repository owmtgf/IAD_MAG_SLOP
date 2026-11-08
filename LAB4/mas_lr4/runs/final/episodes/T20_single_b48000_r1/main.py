def solve(data):
    if data['duration'] == 0:
        return data['start']
    merged = []
    for a, b in sorted(data['windows']):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    remaining = data['duration']
    for a, b in merged:
        effective_start = max(a, data['start'])
        if effective_start >= b:
            continue
        available = b - effective_start
        if remaining <= available:
            return effective_start + remaining
        remaining -= available
    return None
