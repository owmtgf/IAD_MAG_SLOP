def solve(data):
    stock = dict(data['stock'])
    needs = {}
    for item, quantity in data['items']:
        needs[item] = needs.get(item, 0) + quantity
    for item, quantity in needs.items():
        if quantity > stock.get(item, 0):
            return {'ok': False, 'stock': stock}
    for item, quantity in needs.items():
        if quantity:
            stock[item] -= quantity
    return {'ok': True, 'stock': stock}
