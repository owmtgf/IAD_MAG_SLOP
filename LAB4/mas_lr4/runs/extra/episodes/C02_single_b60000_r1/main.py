def solve(data):
    capacity = data['capacity']
    if capacity < 0:
        raise ValueError('capacity')
    if capacity == 0:
        active = []
        accepted = []
        rejected = []
        peak = 0
        for booking in data['bookings']:
            if booking['start'] >= booking['end'] or booking['units'] <= 0:
                raise ValueError('booking')
            rejected.append(booking['id'])
        return {'accepted': accepted, 'rejected': rejected, 'peak': peak}
    active = []
    accepted = []
    rejected = []
    peak = 0
    for booking in data['bookings']:
        if booking['start'] >= booking['end'] or booking['units'] <= 0:
            raise ValueError('booking')
        load = booking['units']
        for previous in active:
            prev_start = previous['start']
            prev_end = previous['end']
            start = booking['start']
            end = booking['end']
            if max(prev_start, start) < min(prev_end, end):
                load += previous['units']
        if load <= capacity:
            active.append(booking)
            accepted.append(booking['id'])
            peak = max(peak, load)
        else:
            rejected.append(booking['id'])
    return {'accepted': accepted, 'rejected': rejected, 'peak': peak}
