def solve(data):
    out = {}
    for department, person, value in data:
        group = out.setdefault(department, {})
        if person not in group:
            group[person] = 0
        group[person] += value
    return out