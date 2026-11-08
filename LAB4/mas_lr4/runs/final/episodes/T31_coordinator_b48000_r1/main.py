def solve(data):
    stock = dict(data['stock'])
    needs = {}
    for item, quantity in data['items']:
        if quantity > 0:
            needs[item] = needs.get(item, 0) + quantity
    for item, quantity in needs.items():
        if stock.get(item, 0) < quantity:
            return {'ok': False, 'stock': stock}
    for item, quantity in needs.items():
        stock[item] -= quantity
    return {'ok': True, 'stock': stock}
