def solve(data):
    remaining = data['budget']
    indices = []
    for i,cost in enumerate(data['costs']):
        if cost <= data['budget']:
            remaining -= cost
            indices.append(i)
    return {'indices':indices,'spent':data['budget']-remaining}
