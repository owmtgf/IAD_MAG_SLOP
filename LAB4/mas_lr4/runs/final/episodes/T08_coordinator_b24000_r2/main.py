def solve(data):
    active = data['end'] - data['start']
    return (data['fee'] * active) // data['days']
