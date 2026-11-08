def solve(data):
    amount = data['amount']
    coins = data['coins']
    if amount == 0:
        return 0
    unreachable = amount + 1
    best = [unreachable] * (amount + 1)
    best[0] = 0
    for value in range(1, amount + 1):
        for coin in coins:
            if coin <= value:
                if best[value - coin] != unreachable:
                    best[value] = min(best[value], best[value - coin] + 1)
    return best[amount] if best[amount] != unreachable else -1