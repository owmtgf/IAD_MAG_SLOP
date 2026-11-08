def solve(data):
    left, right = data['day']
    busy = sorted(data['busy'])
    # Объединяем перекрывающиеся интервалы
    merged = []
    for start, end in busy:
        start, end = max(start, left), min(end, right)
        if start >= end:
            continue
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    
    # Находим свободные интервалы
    gaps = []
    current_edge = left
    for start, end in merged:
        if start > current_edge:
            if end - current_edge > data['min_length']:
                gaps.append([current_edge, start])
        current_edge = max(current_edge, end)
    
    if current_edge < right:
        if right - current_edge > data['min_length']:
            gaps.append([current_edge, right])
    
    return gaps