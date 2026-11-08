def solve(data):
    paid, quantity, returned = data['paid'], data['quantity'], data['returned']
    base = paid // quantity
    extra = paid % quantity
    if returned <= 0:
        return 0
    count_full = min(returned, extra)
    count_partial = max(0, returned - extra)
    return count_full * (base + 1) + count_partial * base