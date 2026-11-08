def solve(data):
    remaining = data['stock']
    fulfilled = []
    for key, quantity in data['orders']:
        taken = min(quantity, remaining)
        remaining -= taken
        fulfilled.append([key, taken])
    return {'fulfilled': fulfilled, 'remaining': remaining}
