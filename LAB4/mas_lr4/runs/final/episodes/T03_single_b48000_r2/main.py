def solve(data):
    paid, quantity, returned = data['paid'], data['quantity'], data['returned']
    base = paid // quantity
    extra = paid % quantity
    # Первые 'extra' единицы получают +1 к стоимости
    full_units = min(returned, extra)
    partial_units = returned - full_units
    return base * returned + full_units
