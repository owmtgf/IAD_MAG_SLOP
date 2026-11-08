def solve(data):
    paid, quantity, returned = data['paid'], data['quantity'], data['returned']
    base = paid // quantity
    extra = paid % quantity
    if returned <= extra:
        return (base + 1) * returned
    else:
        return (base + 1) * extra + base * (returned - extra)