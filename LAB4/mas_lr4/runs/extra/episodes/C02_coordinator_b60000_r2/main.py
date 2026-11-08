def solve(data):
    capacity = data['capacity']
    if capacity < 0:
        raise ValueError('capacity')
    if capacity == 0:
        return {'accepted': [], 'rejected': [b['id'] for b in data['bookings']], 'peak': 0}
    active = []
    accepted = []
    rejected = []
    peak = 0
    for booking in data['bookings']:
        if booking['start'] >= booking['end'] or booking['units'] <= 0:
            raise ValueError('booking')
        load = booking['units']
        conflict_load = 0
        for previous in active:
            if previous['start'] < booking['end'] and booking['start'] < previous['end']:
                conflict_load += previous['units']
        total_load = load + conflict_load
        if total_load <= capacity:
            active.append(booking)
            accepted.append(booking['id'])
            current_load = sum(b['units'] for b in active)
            peak = max(peak, current_load)
        else:
            rejected.append(booking['id'])
    return {'accepted': accepted, 'rejected': rejected, 'peak': peak}
