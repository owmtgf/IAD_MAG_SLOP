def solve(data):
    base_fee = data['base_fee']
    grams = data['grams']
    base_grams = data['base_grams']
    step_grams = data['step_grams']
    step_fee = data['step_fee']
    if grams > base_grams:
        extra = grams - base_grams
        steps = (extra + step_grams - 1) // step_grams
    else:
        steps = 0
    return base_fee + steps * step_fee