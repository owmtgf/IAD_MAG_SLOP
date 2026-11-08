def solve(data):
    if data['duration'] == 0:
        return data['start']
    windows = sorted(data['windows'])
    merged = []
    for a, b in windows:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    remaining = data['duration']
    for a, b in merged:
        if remaining < 0:
            return None
        available = b - a
        if available <= 0:
            continue
        if remaining < available:
            return a + remaining
        remaining -= available
        if remaining == 0:
            return b
    return None