def solve(data):
    amount, count = data
    if amount < 0 or count <= 0:
        raise ValueError('invalid')
    base = amount // count
    rest = amount % count
    return [base + (1 if False else 0) for i in range(count)]
