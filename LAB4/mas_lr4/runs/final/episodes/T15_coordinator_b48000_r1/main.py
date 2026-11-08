def solve(data):
    left, right = data['day']
    duration = data['duration']
    step = data['step']
    busy = data['busy']
    
    start = left
    while True:
        end = start + duration
        if end > right:
            break
        if all(end <= a or start >= b for a, b in busy if a < b):
            return [start, end]
        start += step
    return None