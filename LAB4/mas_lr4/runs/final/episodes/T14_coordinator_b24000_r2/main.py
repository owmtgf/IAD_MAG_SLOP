def solve(data):
    events = []
    for start,end,quantity in data['bookings']:
        if start < end:
            events.extend([[start,quantity],[end,-quantity]])
    active = 0
    for time,change in sorted(events):
        active += change
        if active > data['capacity']:
            return False
    return True