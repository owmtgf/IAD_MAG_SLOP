def solve(data):
    capacity = data['capacity']
    if capacity < 0:
        raise ValueError('capacity')
    if capacity == 0:
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
        start = booking['start']
        end = booking['end']
        units = booking['units']
        current_load = units
        for prev in active:
            p_start = prev['start']
            p_end = prev['end']
            p_units = prev['units']
            if p_start < end and start < p_end:
                current_load += p_units
        if current_load <= capacity:
            active.append(booking)
            accepted.append(booking['id'])
            peak = max(peak, current_load)
        else:
            rejected.append(booking['id'])
    return {'accepted': accepted, 'rejected': rejected, 'peak': peak}
