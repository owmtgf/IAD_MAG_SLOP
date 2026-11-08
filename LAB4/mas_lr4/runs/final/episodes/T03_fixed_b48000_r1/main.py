def solve(data):
    paid, quantity, returned = data['paid'], data['quantity'], data['returned']
    base = paid // quantity
    extra = paid % quantity
    full_units = min(returned, quantity - extra)
    extra_units = max(0, returned - (quantity - extra))
    return base * full_units + extra * extra_units
