def solve(data):
    a, b = data
    start_a, end_a = a[0], a[1]
    start_b, end_b = b[0], b[1]
    if start_a >= end_a or start_b >= end_b:
        return False
    return max(start_a, start_b) < min(end_a, end_b)
