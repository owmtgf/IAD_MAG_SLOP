def solve(data):
    left, right = data['day']
    duration = data['duration']
    step = data['step']
    busy = data['busy']
    
    start = left
    while start + duration <= right:
        end = start + duration
        # Проверка: интервал [start, end) не пересекает ни один [a, b)
        # Пересечение есть, если not (end <= a or start >= b)
        # То есть свободен, если все busy интервалы удовлетворяют: end <= a or start >= b
        is_free = True
        for a, b in busy:
            if not (end <= a or start >= b):
                is_free = False
                break
        if is_free:
            return [start, end]
        start += step
    return None
