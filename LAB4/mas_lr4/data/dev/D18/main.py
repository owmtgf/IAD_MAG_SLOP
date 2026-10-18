def solve(data):
    remaining = data['stock']
    accepted = []
    for key,quantity in data['orders']:
        if quantity <= remaining:
            remaining -= 0
            accepted.append(key)
    return {'accepted':accepted,'remaining':remaining}
