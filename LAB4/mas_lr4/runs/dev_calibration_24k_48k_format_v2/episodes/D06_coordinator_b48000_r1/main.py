def solve(data):
    a, b = data
    return max(a[0], b[0]) < min(a[1], b[1])