def solve(data):
    left, right = data['day']
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
                    merged.append([s, e])
                    start, end = s, e
    else:
        merged = [left, right]
    
    result = []
    if len(merged) == 0:
        if right - left >= data['min_length']:
            result.append([left, right])
    else:
        for i in range(len(merged) - 1):
            start, end = merged[i]
            next_start, next_end = merged[i + 1]
            gap_len = next_start - end
            if gap_len >= data['min_length']:
                result.append([start, end])
        if right - merged[-1][1] >= data['min_length']:
            result.append([merged[-1][1], right])
    
    return result