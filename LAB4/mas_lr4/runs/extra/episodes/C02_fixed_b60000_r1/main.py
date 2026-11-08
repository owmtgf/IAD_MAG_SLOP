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
        current_load = booking['units']
        for prev in active:
            if prev['start'] <= booking['end'] and booking['start'] <= prev['end']:
                current_load += prev['units']
        if current_load <= capacity:
            active.append(booking)
            accepted.append(booking['id'])
            peak = max(peak, current_load)
        else:
            rejected.append(booking['id'])
    return {'accepted': accepted, 'rejected': rejected, 'peak': peak}
