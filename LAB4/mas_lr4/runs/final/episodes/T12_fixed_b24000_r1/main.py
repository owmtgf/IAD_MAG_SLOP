def solve(data):
    left, right = data['day']
    min_len = data['min_length']
    busy = sorted(data['busy'])
    edge = left
    result = []
    for start, end in busy:
        start = max(start, left)
        end = min(end, right)
        if start >= end:
            continue
        if start <= edge:
            edge = max(edge, end)
        else:
            if edge < right:
                if edge - left >= min_len:
                    result.append([left, edge])
                left = edge
            edge = end
    if left < right:
        if edge - left >= min_len:
            result.append([left, edge])
    return result
