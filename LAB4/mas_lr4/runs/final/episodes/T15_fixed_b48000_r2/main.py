def solve(data):
    left, right = data['day']
    duration = data['duration']
    step = data['step']
    start = left
    while start + duration <= right:
        end = start + duration
        if all(end <= a or start >= b for a, b in data['busy'] if a < b):
            return [start, end]
        start += step
    return None