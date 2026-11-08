def solve(data):
    prices = sorted(data['prices'])
    free = len(prices) // data['every']
    return sum(prices[free:])