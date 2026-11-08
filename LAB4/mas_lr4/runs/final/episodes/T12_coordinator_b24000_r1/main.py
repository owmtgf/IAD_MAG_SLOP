def solve(data):
    left, right = data['day']
    edge = left
    gaps = []
    for start, end in sorted(data['busy']):
        start, end = max(start, left), min(end, right)
        if start >= end:
            continue
        if start > edge:
            gaps.append([edge, start])
        edge = max(edge, end)
    if edge < right:
        gaps.append([edge, right])
    return [g for g in gaps if g[1] - g[0] >= data['min_length']]
