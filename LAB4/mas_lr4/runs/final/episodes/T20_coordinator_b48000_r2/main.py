def solve(data):
    if data['duration'] == 0:
        return data['start']
    merged = []
    for a,b in sorted(data['windows']):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1],b)
        else:
            merged.append([a,b])
    remaining = data['duration']
    current_time = data['start']
    for a,b in merged:
        if current_time < a:
            current_time = a
        available = max(0, b - current_time)
        if remaining < available:
            return None
        remaining -= available
        current_time = b
    return current_time + remaining