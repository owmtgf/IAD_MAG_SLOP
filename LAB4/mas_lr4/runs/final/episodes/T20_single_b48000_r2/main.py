def solve(data):
    if data['duration'] == 0:
        return data['start']
    merged = []
    for a, b in sorted(data['windows']):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    
    current_time = data['start']
    remaining = data['duration']
    
    for a, b in merged:
        if current_time >= b:
            continue
        
        available = b - current_time
        if remaining <= available:
            return current_time + remaining
        remaining -= available
        current_time = b
    
    return None
