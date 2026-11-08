def solve(data):
    left, right = data['base']
    if left >= right:
        return []
    
    blocked = data['blocked']
    pieces = [[left, right]]
    
    for a, b in blocked:
        if a >= b:
            continue
        
        next_pieces = []
        for start, end in pieces:
            # Если интервал полностью вне блока (слева или справа)
            if b <= start or a >= end:
                next_pieces.append([start, end])
            else:
                # Если есть пересечение, разбиваем интервал
                # Левая часть: от start до начала блока (если start < a)
                if start < a:
                    next_pieces.append([start, a])
                # Правая часть: от конца блока до end (если b < end)
                if b < end:
                    next_pieces.append([b, end])
        pieces = next_pieces
    
    # Фильтруем пустые интервалы и сортируем по порядку
    result = []
    current_start = left
    for start, end in pieces:
        if start > current_start:
            result.append([current_start, start])
        current_start = max(current_start, end)
    if current_start < right:
        result.append([current_start, right])
    
    return result