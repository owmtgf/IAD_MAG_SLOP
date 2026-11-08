def solve(data):
    paid, quantity, returned = data['paid'], data['quantity'], data['returned']
    base = paid // quantity
    extra = paid % quantity
    total = 0
    for i in range(returned):
        if i < extra:
            total += base + 1
        else:
            total += base
    return total