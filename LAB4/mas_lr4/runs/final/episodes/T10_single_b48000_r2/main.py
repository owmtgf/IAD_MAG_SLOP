def solve(data):
    debts = data['debts']
    budget = data['budget']
    n = len(debts)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: (debts[i]['due'], debts[i]['id']))
    paid = [0] * n
    for idx in order:
        if budget <= 0:
            break
        amount = debts[idx]['amount']
        pay = min(amount, budget)
        paid[idx] = pay
        budget -= pay
    return [[debt['id'], paid[i]] for i in range(n)]