def solve(data):
    stock = dict(data['stock'])
    item = data['item']
    quantity = data['quantity']
    current = stock.get(item, 0)
    if current < quantity:
        return {'ok': False, 'stock': stock}
    if quantity > 0:
        stock[item] = current - quantity
    return {'ok': True, 'stock': stock}
