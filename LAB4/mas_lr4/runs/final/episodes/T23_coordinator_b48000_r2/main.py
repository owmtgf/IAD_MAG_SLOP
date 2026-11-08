def solve(data):
    out = {}
    for department, person, value in data:
        if department not in out:
            out[department] = {}
        group = out[department]
        if person not in group:
            group[person] = 0
        group[person] += value
    return out