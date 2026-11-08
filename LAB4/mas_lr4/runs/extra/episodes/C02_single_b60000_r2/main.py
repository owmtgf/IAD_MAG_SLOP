def solve(data):
    capacity = data['capacity']
    if capacity < 0:
        raise ValueError('capacity')
    active = []
    accepted = []
    rejected = []
    peak = 0
    for booking in data['bookings']:
        if booking['start'] >= booking['end'] or booking['units'] <= 0:
            raise ValueError('booking')
        load = booking['units']
        for previous in active:
            if previous['start'] <= booking['end'] and booking['start'] <= previous['end']:
                load += previous['units']
        if load <= capacity:
            active.append(booking)
            accepted.append(booking['id'])
            peak = max(peak, load)
        else:
            rejected.append(booking['id'])
    return {'accepted': accepted, 'rejected': rejected, 'peak': peak}
