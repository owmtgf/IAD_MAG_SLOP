def solve(data):
    if data['duration'] == 0:
        return data['start']
    merged = []
    for a,b in sorted(data['windows']):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    remaining = data['duration']
    for a, b in merged:
        available = b - a
        if remaining < available:
            return b + remaining
        remaining -= available
    return None