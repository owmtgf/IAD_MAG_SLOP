def solve(data):
    total = 0
    for price, quantity in data:
        if price < 0 or quantity < 0:
            raise ValueError('negative')
        total += price * quantity
    return total
