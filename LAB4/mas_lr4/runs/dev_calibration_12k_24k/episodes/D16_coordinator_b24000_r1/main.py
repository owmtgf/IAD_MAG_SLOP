def solve(data):
    stock = dict(data['stock'])
    item = data['item']
    quantity = data['quantity']
    if stock.get(item, 0) < quantity:
        return {'ok': False, 'stock': stock}
    if quantity > 0:
        stock[item] -= quantity
    return {'ok': True, 'stock': stock}
