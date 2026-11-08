def solve(data):
    left, right = data['day']
    duration = data['duration']
    step = data['step']
    busy = data['busy']
    
    # Если busy пустой, проверяем, помещается ли интервал в day
    if not busy:
        if right - left >= duration:
            return [left, left + duration]
        return None
    
    # Сортируем busy по началу, затем по концу
    busy_sorted = sorted(busy, key=lambda x: (x[0], x[1]))
    
    # Проверяем каждый возможный старт: left + k*step
    start = left
    while True:
        end = start + duration
        
        # Если интервал выходит за пределы day, больше проверять не нужно
        if end > right:
            break
        
        # Проверяем пересечение с busy интервалами
        # Интервал [start, end) пересекает [b_start, b_end), если start < b_end и end > b_start
        conflict = False
        for b_start, b_end in busy_sorted:
            if start < b_end and end > b_start:
                conflict = True
                break
        
        if not conflict:
            return [start, end]
        
        # Если шаг больше, чем расстояние до следующего busy или до конца day, выходим
        if step == 0:
            break
        next_start = start + step
        if next_start >= right:
            break
        start = next_start
    
    return None
