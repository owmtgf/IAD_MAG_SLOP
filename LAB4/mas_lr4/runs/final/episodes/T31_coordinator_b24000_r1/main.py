def solve(data):
    stock = dict(data['stock'])
    needs = {}
    for item, quantity in data['items']:
        needs[item] = needs.get(item, 0) + quantity
    for item, quantity in needs.items():
        if quantity > 0 and stock.get(item, 0) < quantity:
            return {'ok': False, 'stock': stock}
    for item, quantity in needs.items():
        if quantity > 0:
            stock[item] -= quantity
    return {'ok': True, 'stock': stock}
