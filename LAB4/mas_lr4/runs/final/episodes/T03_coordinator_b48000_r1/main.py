def solve(data):
    paid, quantity, returned = data['paid'], data['quantity'], data['returned']
    base = paid // quantity
    extra = paid % quantity
    # Первые 'extra' единицы получают +1 к цене
    # Если returned <= extra, то все returned единиц имеют цену base + 1
    # Если returned > extra, то первые extra имеют цену base + 1, остальные (returned - extra) имеют цену base
    if returned <= extra:
        return (base + 1) * returned
    else:
        return (base + 1) * extra + base * (returned - extra)
