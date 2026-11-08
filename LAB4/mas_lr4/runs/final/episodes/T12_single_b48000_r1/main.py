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
            for i in range(1, len(busy)):
                s, e = busy[i]
                s, e = max(s, left), min(e, right)
                if s < end:
                    end = max(end, e)
                else:
                    merged.append([s, end])
                    start, end = s, e
    else:
        merged = [left, right]
    result = []
    if len(merged) == 1:
        if merged[0][1] < right:
            gap_start, gap_end = merged[0][1], right
            if gap_end - gap_start >= min_len:
                result.append([gap_start, gap_end])
    else:
        for i in range(len(merged) - 1):
            if merged[i][1] < merged[i+1][0]:
                gap_start, gap_end = merged[i][1], merged[i+1][0]
                if gap_end - gap_start >= min_len:
                    result.append([gap_start, gap_end])
        if merged[-1][1] < right:
            gap_start, gap_end = merged[-1][1], right
            if gap_end - gap_start >= min_len:
                result.append([gap_start, gap_end])
    return result
