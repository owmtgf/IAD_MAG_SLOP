def solve(data):
    stock = dict(data['stock'])
    needs = {}
    for item, quantity in data['items']:
        needs[item] = quantity
    
    total_needed = 0
    for item, quantity in needs.items():
        available = stock.get(item, 0)
        if quantity > available:
            return {'ok': False, 'stock': stock}
        total_needed += quantity
    
    for item, quantity in needs.items():
        if quantity > 0:
            stock[item] -= quantity
    
    return {'ok': True, 'stock': stock}
