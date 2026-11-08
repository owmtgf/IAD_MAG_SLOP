def solve(data):
    stock = data['stock']
    seen = set()
    rejected = []
    for event in data['events']:
        if event['id'] in seen:
            continue
        seen.add(event['id'])
        new_stock = stock + event['delta']
        if new_stock < 0:
            rejected.append(event['id'])
        else:
            stock = new_stock
    return {'stock': stock, 'rejected': rejected}
