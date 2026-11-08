def solve(data):
    events = []
    for start, end, quantity in data['bookings']:
        if start < end:
            events.append((start, quantity))
            events.append((end, -quantity))
    events.sort(key=lambda x: (x[0], x[1]))
    active = 0
    for time, change in events:
        active += change
        if active > data['capacity']:
            return False
    return True