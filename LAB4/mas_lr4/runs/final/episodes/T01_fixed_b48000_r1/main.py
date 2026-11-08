def solve(data):
    amount = data['amount']
    for percent in data['discounts']:
        discount = amount * percent // 100
        amount -= discount
    return amount