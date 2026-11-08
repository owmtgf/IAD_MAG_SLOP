def solve(data):
    events = []
    for start,end in data:
        if start < end:
            events.append([start,1])
            events.append([end,-1])
    events.sort(key=lambda x:(x[0],x[1]))
    active = peak = 0
    for time,change in events:
        active += change
        peak = max(peak,active)
    return peak