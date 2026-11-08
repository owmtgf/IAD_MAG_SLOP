def solve(data):
    amount = data['amount']
    unreachable = amount + 1
    best = [0] + [unreachable] * amount
    for value in range(1, amount + 1):
        for coin in data['coins']:
            if coin <= value:
                prev = value - coin
                if prev >= 0:
                    best[value] = min(best[value], best[prev] + 1)
    return best[amount] if best[amount] != unreachable else -1