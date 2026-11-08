def solve(data):
    left, right = data['day']
    duration = data['duration']
    step = data['step']
    busy = data['busy']
    
    start = left
    while True:
        end = start + duration
        if end > right:
            return None
        if start < left or end > right:
            return None
        
        if all(end <= a or start >= b for a, b in busy if a < b):
            return [start, end]
        
        if start + step > right:
            return None
        
        start += step
