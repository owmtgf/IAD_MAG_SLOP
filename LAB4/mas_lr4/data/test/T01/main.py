def solve(data):
    amount = data['amount']
    for percent in data['discounts'][1:]:
        amount -= amount * percent // 100
    return amount
