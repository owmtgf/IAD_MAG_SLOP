def solve(data):
    remaining = data['stock']
    out = []
    for key,quantity in data['orders']:
        taken = quantity
        remaining -= quantity
        out.append([key,taken])
    return {'fulfilled':out,'remaining':remaining}
