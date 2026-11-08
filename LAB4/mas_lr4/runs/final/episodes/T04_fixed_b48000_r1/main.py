def solve(data):
    prices, discount = data['prices'], data['discount']
    total = sum(prices)
    if total == 0:
        return [0 for p in prices]
    shares = [discount * p // total for p in prices]
    remainder = discount - sum(shares)
    order = sorted(range(len(prices)), key=lambda i: (-(discount * prices[i] % total), i))
    for i in order[:remainder]:
        shares[i] += 1
    return shares