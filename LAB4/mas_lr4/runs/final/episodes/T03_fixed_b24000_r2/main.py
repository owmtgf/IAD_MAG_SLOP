def solve(data):
    paid, quantity, returned = data['paid'], data['quantity'], data['returned']
    base = paid // quantity
    extra = paid % quantity
    if returned <= extra:
        return returned * (base + 1)
    else:
        return extra * (base + 1) + (returned - extra) * base
