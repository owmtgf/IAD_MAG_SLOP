def solve(data):
    amount = data['amount']
    base = amount
    extra = max(0, amount - data['threshold'])
    return (base * data['low'] + extra * data['high']) // 100
