def solve(data):
    extra = max(0, data['grams'] - data['base_grams'])
    steps = (extra + data['step_grams'] - 1) // data['step_grams'] if extra > 0 else 0
    return data['base_fee'] + steps * data['step_fee']