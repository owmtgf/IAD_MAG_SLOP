def solve(data):
    stock = dict(data['stock'])
    source, target, q = data['source'], data['target'], data['quantity']
    if source == target or q == 0:
        return {'ok': True, 'stock': stock}
    if stock.get(source, 0) < q:
        return {'ok': False, 'stock': stock}
    stock[source] -= q
    stock[target] = stock.get(target, 0) + q
    return {'ok': True, 'stock': stock}
