def solve(data):
    base_fee = data['base_fee']
    extra = data['grams'] - data['base_grams']
    if extra <= 0:
        return base_fee
    steps = (extra + data['step_grams'] - 1) // data['step_grams']
    return base_fee + steps * data['step_fee']