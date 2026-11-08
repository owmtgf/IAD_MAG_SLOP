def solve(data):
    paid, quantity, returned = data['paid'], data['quantity'], data['returned']
    base = paid // quantity
    extra = paid % quantity
    if returned <= extra:
        return base * returned + returned
    else:
        return base * returned + extra
