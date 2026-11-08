def solve(data):
    out = {}
    for department, person, value in data:
        if department not in out:
            out[department] = {}
        if person not in out[department]:
            out[department][person] = 0
        out[department][person] += value
    return out