def solve(data):
    left, right = data['base']
    pieces = [[left, right]] if left < right else []
    for a, b in data['blocked']:
        if a >= b:
            continue
        next_pieces = []
        for start, end in pieces:
            if b <= start or a >= end:
                next_pieces.append([start, end])
            else:
                if start < a:
                    next_pieces.append([start, a])
                if b < end:
                    next_pieces.append([b, end])
        pieces = next_pieces
    return pieces
