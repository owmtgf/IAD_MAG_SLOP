def solve(data):
    stock = data['stock']
    item,quantity = data['item'],data['quantity']
    if stock.get(item,0) < quantity:
        return {'ok':False,'stock':stock}
    if quantity:
        stock[item] -= quantity
    return {'ok':True,'stock':stock}
