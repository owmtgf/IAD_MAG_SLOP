def solve(data):
    remaining = data['stock']
    out = []
    for key, quantity in data['orders']:
        if remaining >= quantity:
            taken = quantity
        else:
            taken = remaining
        remaining -= taken
        out.append([key, taken])
    return {'fulfilled': out, 'remaining': remaining}
