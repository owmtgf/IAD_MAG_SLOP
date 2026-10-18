def solve(data):
    paid, quantity, returned = data['paid'], data['quantity'], data['returned']
    base = paid // quantity
    extra = paid % quantity
    return base * returned
