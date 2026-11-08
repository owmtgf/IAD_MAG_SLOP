def solve(data):
    events = []
    for start,end,quantity in data['bookings']:
        if start < end:
            events.extend([[start,quantity],[end,-quantity]])
    events.sort()
    active = 0
    for time,change in events:
        active += change
        if active > data['capacity']:
            return False
    return True