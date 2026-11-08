def solve(data):
    cap = data['amount'] * data['cap_percent'] // 100
    max_by_value = cap // data['value']
    used = min(max_by_value, data['points'])
    return {'used': used, 'due': data['amount'] - used * data['value']}
