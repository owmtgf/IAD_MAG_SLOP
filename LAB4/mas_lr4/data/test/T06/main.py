def solve(data):
    extra = max(0, data['grams'] - data['base_grams'])
    steps = extra // data['step_grams']
    return steps * data['step_fee']
