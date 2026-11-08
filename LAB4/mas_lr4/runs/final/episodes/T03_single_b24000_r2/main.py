def solve(data):
    paid, quantity, returned = data['paid'], data['quantity'], data['returned']
    base = paid // quantity
    extra = paid % quantity
    # Первые 'extra' единиц получают +1 к цене
    # Если returned <= extra, цена каждой единицы = base + 1
    # Иначе, первые 'extra' стоят base + 1, остальные base
    if returned <= extra:
        return (base + 1) * returned
    else:
        return (base + 1) * extra + base * (returned - extra)
