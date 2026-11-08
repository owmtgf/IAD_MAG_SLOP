def solve(data):
    active_days = data['end'] - data['start']
    return (data['fee'] * active_days) // data['days']