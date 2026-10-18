def solve(data):
    start, end = data['request']
    left, right = data['day']
    if not (left <= start < end <= right):
        return False
    return all(end < a or start > b for a,b in data['busy'] if a < b)
