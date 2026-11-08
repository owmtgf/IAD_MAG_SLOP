def solve(data):
    days = data['days']
    start = data['start']
    end = data['end']
    fee = data['fee']
    active_days = end - start
    return fee * active_days // days
