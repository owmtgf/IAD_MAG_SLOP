def solve(data):
    capacity = data['capacity']
    if capacity < 0:
        raise ValueError('capacity')
    if capacity == 0:
        return {'accepted': [], 'rejected': [b['id'] for b in data['bookings']], 'peak': 0}
    
    def get_max_load(intervals):
        if not intervals:
            return 0
        events = []
        for s, e, u in intervals:
            events.append((s, 1, u))
            events.append((e, -1, u))
        events.sort(key=lambda x: (x[0], x[1]))
        current_load = 0
        max_load = 0
        for _, delta, _ in events:
            current_load += delta
            if current_load > max_load:
                max_load = current_load
        return max_load
    
    accepted = []
    rejected = []
    
    for booking in data['bookings']:
        if booking['start'] >= booking['end'] or booking['units'] <= 0:
            raise ValueError('booking')
        
        test_intervals = [(b['start'], b['end'], b['units']) for b in accepted] + [(booking['start'], booking['end'], booking['units'])]
        max_load = get_max_load(test_intervals)
        
        if max_load <= capacity:
            accepted.append(booking)
        else:
            rejected.append(booking)
    
    peak = get_max_load([(b['start'], b['end'], b['units']) for b in accepted])
    return {'accepted': [b['id'] for b in accepted], 'rejected': [b['id'] for b in rejected], 'peak': peak}
