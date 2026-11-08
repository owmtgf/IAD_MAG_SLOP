def solve(data):
    base_fee = data['base_fee']
    if data['grams'] <= data['base_grams']:
        return base_fee
    extra = data['grams'] - data['base_grams']
    steps = (extra + data['step_grams'] - 1) // data['step_grams']
    return base_fee + steps * data['step_fee']