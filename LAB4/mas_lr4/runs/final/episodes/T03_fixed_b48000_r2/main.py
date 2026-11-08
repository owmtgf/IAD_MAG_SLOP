def solve(data):
    paid, quantity, returned = data['paid'], data['quantity'], data['returned']
    base = paid // quantity
    extra = paid % quantity
    # Первые 'extra' единиц стоят base + 1, остальные — base
    # Если returned <= extra, то первые returned стоят base + 1
    # Иначе, первые extra стоят base + 1, а следующие (returned - extra) стоят base
    if returned <= extra:
        return (base + 1) * returned
    else:
        return (base + 1) * extra + base * (returned - extra)
