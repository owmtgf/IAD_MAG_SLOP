def solve(data):
    a, b = data
    start = max(a[0], b[0])
    end = min(a[1], b[1])
    return start < end