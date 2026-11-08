def solve(data):
    extra = max(0, data['grams'] - data['base_grams'])
    if extra == 0:
        steps = 0
    else:
        steps = (extra + data['step_grams'] - 1) // data['step_grams']
    total = steps * data['step_fee'] + data['base_fee']
    return total
