def solve(data):
    left, right = data['day']
    start = left
    while start + data['duration'] <= right:
        end = start + data['duration']
        if all(end <= a or start >= b for a, b in data['busy'] if a < b):
            return [start, end]
        start += data['step']
    return None