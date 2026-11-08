def solve(data):
    left, right = data['day']
    min_len = data['min_length']
    busy = sorted(data['busy'])
    merged = []
    if busy:
        start, end = busy[0]
        start, end = max(start, left), min(end, right)
        if start < end:
            merged.append([start, end])
        for s, e in busy[1:]:
            s, e = max(s, left), min(e, right)
            if s < end:
                end = max(end, e)
            else:
                merged.append([s, e])
    else:
        merged = [left, right]
    result = []
    for i in range(len(merged) - 1):
        if merged[i][1] < merged[i+1][0]:
            gap_start = merged[i][1]
            gap_end = merged[i+1][0]
            if gap_end - gap_start >= min_len:
                result.append([gap_start, gap_end])
    if len(merged) > 1 and merged[-1][1] < right:
        if right - merged[-1][1] >= min_len:
            result.append([merged[-1][1], right])
    return result