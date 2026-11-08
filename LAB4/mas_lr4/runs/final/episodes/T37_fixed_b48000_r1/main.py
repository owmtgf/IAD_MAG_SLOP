def solve(data):
    stock = data['stock']
    seen = set()
    rejected = []
    for event in data['events']:
        eid = event['id']
        if eid in seen:
            continue
        seen.add(eid)
        if stock + event['delta'] < 0:
            rejected.append(eid)
        else:
            stock += event['delta']
    return {'stock': stock, 'rejected': rejected}
