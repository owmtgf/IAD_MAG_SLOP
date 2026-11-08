def solve(data):
    cap = data['amount'] * data['cap_percent'] // 100
    max_possible = cap // data['value']
    used = min(max_possible, data['points'])
    return {'used': used, 'due': data['amount'] - used * data['value']}
