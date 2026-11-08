def solve(data):
    out = {}
    for department, person, value in data:
        group = out.setdefault(department, {})
        if person not in group:
            group[person] = value
        else:
            group[person] += value
    return out