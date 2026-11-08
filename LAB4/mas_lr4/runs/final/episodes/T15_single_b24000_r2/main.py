def solve(data):
    left, right = data['day']
    duration = data['duration']
    step = data['step']
    busy = data['busy']
    
    start = left
    while start + duration <= right:
        end = start + duration
        # Проверяем, что интервал [start, end) не пересекает ни одного busy [a, b)
        # Пересечение есть, если max(start, a) < min(end, b)
        # Отсутствует, если start >= b или end <= a
        is_free = True
        for a, b in busy:
            if end <= a or start >= b:
                continue
            # Пересечение есть: max(start, a) < min(end, b)
            if max(start, a) < min(end, b):
                is_free = False
                break
        if is_free:
            return [start, end]
        start += step
    return None