def solve(data):
    ends = []
    assigned = [0] * len(data)
    for i in sorted(range(len(data)),key=lambda i:(data[i][0],i)):
        start,end = data[i]
        room = next((j for j in range(len(ends)) if ends[j] < start),len(ends))
        if room == len(ends):
            ends.append(end)
        else:
            ends[room] = start
        assigned[i] = room
    return assigned
