def solve(data):
    cap = data['amount'] * data['cap_percent'] // 100
    used = cap // data['value']
    return {'used': used, 'due': data['amount'] - used * data['value']}
