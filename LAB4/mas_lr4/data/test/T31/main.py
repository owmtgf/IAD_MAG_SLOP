def solve(data):
    stock = dict(data['stock'])
    needs = {}
    for item,quantity in data['items']:
        needs[item] = quantity
    if any(quantity > stock.get(item,0) for item,quantity in needs.items()):
        return {'ok':False,'stock':stock}
    for item,quantity in needs.items():
        if quantity:
            stock[item] -= quantity
    return {'ok':True,'stock':stock}
