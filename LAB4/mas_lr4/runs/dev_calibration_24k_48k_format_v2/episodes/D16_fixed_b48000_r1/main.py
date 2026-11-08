def solve(data):
    stock = data['stock']
    item, quantity = data['item'], data['quantity']
    current_stock = stock.get(item, 0)
    if current_stock < quantity:
        return {'ok': False, 'stock': stock}
    if quantity > 0:
        new_stock = dict(stock)
        new_stock[item] = current_stock - quantity
        return {'ok': True, 'stock': new_stock}
    return {'ok': True, 'stock': stock}
