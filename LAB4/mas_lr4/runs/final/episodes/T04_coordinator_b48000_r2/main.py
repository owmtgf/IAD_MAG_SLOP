def solve(data):
    prices, discount = data['prices'], data['discount']
    total = sum(prices)
    if total == 0:
        return [0 for p in prices]
    shares = [discount * p // total for p in prices]
    order = sorted(range(len(prices)), key=lambda i: (-(discount * prices[i] % total), i))
    remaining = discount - sum(shares)
    for i in order[:remaining]:
        shares[i] += 1
    return shares