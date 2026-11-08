def solve(data):
    cap = data['amount'] * data['cap_percent'] // 100
    max_points = min(cap, data['points'])
    used = max_points // data['value']
    return {'used': used, 'due': data['amount'] - used * data['value']}
