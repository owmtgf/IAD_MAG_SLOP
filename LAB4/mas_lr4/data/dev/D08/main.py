def solve(data):
    total = 0
    edge = None
    for start, end in sorted(data):
        if edge is None or start >= edge:
            total += end - start
        elif end > edge:
            total += end - edge
        edge = end if edge is None else end
    return total
