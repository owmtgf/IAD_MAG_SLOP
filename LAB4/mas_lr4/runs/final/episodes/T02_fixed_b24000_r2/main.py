def solve(data):
    prices = sorted(data['prices'])
    free_count = len(prices) // data['every']
    return sum(prices[free_count:])