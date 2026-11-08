def solve(data):
    left, right = data['day']
    duration = data['duration']
    step = data['step']
    busy = data['busy']
    
    start = left
    while start + duration <= right:
        end = start + duration
        is_free = True
        for a, b in busy:
            if end > a and start < b:
                is_free = False
                break
        if is_free:
            return [start, end]
        start += step
    return None