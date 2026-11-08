def solve(data):
    remaining = data['stock']
    out = []
    for key, quantity in data['orders']:
        taken = min(quantity, remaining)
        remaining -= taken
        out.append([key, taken])
    return {'fulfilled': out, 'remaining': remaining}
