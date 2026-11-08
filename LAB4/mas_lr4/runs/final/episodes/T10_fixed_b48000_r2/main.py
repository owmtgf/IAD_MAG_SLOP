def solve(data):
    debts = data['debts']
    budget = data['budget']
    n = len(debts)
    order = sorted(range(n), key=lambda i: (debts[i]['due'], debts[i]['id']))
    paid = [0] * n
    for idx in order:
        if budget <= 0:
            break
        amount = debts[idx]['amount']
        to_pay = min(amount, budget)
        paid[idx] = to_pay
        budget -= to_pay
    return [[debt['id'], paid[i]] for i, debt in enumerate(debts)]