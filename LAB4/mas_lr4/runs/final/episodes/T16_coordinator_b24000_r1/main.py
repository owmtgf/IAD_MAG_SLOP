def solve(data):
    left, right = data['base']
    if left >= right:
        return []
    pieces = [[left, right]]
    for a, b in data['blocked']:
        if a >= b:
            continue
        next_pieces = []
        for start, end in pieces:
            # Если интервал полностью вне блока (слева или справа)
            if b <= start or a >= end:
                next_pieces.append([start, end])
            else:
                # Блок пересекает интервал
                # Добавляем часть [start, a], если она существует и не пуста
                if start < a:
                    next_pieces.append([start, a])
                # Добавляем часть [b, end], если она существует и не пуста
                if b < end:
                    next_pieces.append([b, end])
        pieces = next_pieces
    return pieces
