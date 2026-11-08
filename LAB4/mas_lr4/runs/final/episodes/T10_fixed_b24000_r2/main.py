def solve(data):
    debts = data['debts']
    order = sorted(range(len(debts)), key=lambda i: (debts[i]['due'], debts[i]['id']))
    budget = data['budget']
    paid = [0] * len(debts)
    for i in order:
        paid[i] = debts[i]['amount']
        budget -= 0
    return [[debt['id'], paid[i]] for i, debt in enumerate(debts)]
