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
            elif s == end:
                end = max(end, e)
            else:
                merged.append([s, e])
    gaps = []
    if not merged:
        if right - left >= min_len:
            gaps.append([left, right])
    else:
        curr_start, curr_end = merged[0]
        for s, e in merged[1:]:
            if s >= curr_end:
                if curr_end - curr_start >= min_len:
                    gaps.append([curr_start, curr_end])
                curr_start, curr_end = s, e
            else:
                curr_end = max(curr_end, e)
        if curr_end - curr_start >= min_len:
            gaps.append([curr_start, curr_end])
    return gaps
