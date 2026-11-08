def solve(data):
    if data['duration'] == 0:
        return data['start']
    merged = []
    for a,b in sorted(data['windows']):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    if not merged:
        return None
    remaining = data['duration']
    for a, b in merged:
        if remaining <= 0:
            break
        available = b - a
        if remaining < available:
            return a + remaining
        remaining -= available
    return None