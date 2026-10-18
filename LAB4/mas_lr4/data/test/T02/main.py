def solve(data):
    prices = sorted(data['prices'], reverse=True)
    free = len(prices) // data['every']
    return sum(prices[free:])
