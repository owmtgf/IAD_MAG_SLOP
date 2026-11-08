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
    current_time = data['start']
    for a, b in merged:
        start_interval = max(current_time, a)
        if start_interval >= b:
            break
        available = b - start_interval
        if remaining < available:
            return current_time + remaining
        remaining -= available
        current_time = b
    return None