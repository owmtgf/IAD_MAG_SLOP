def solve(data):
    amount = data['amount']
    unreachable = amount + 1
    best = [0] + [unreachable] * amount
    for value in range(1, amount):
        for coin in data['coins']:
            if coin < value:
                best[value] = min(best[value], best[value - coin] + 1)
    return best[amount] if best[amount] != unreachable else -1
