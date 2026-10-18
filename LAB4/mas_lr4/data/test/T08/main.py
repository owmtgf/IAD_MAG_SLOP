def solve(data):
    active = data['end'] - data['start'] + 1
    return (data['fee'] // data['days']) * active
