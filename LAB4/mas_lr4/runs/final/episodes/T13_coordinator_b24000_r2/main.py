def solve(data):
    events = []
    for start,end in data:
        if start < end:
            events.append([start,1])
            events.append([end,-1])
    active = peak = 0
    for time,change in sorted(events, key=lambda x:(x[0], x[1])):
        active += change
        peak = max(peak,active)
    return peak
