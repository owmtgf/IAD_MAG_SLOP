def solve(data):
    stock = data['stock']
    seen = set()
    rejected = []
    for event in data['events']:
        if event['id'] in seen:
            continue
        seen.add(event['id'])
        if stock + event['delta'] < 0:
            rejected.append(event['id'])
        else:
            stock += event['delta']
    return {'stock': stock, 'rejected': rejected}
