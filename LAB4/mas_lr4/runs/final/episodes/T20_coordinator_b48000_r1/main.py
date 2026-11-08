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
        if current_time >= b:
            continue
        start_work = max(current_time, a)
        if start_work >= b:
            continue
        available = b - start_work
        if remaining < available:
            return start_work + remaining
        if remaining == 0:
            return start_work
        remaining -= available
        current_time = b
    return None