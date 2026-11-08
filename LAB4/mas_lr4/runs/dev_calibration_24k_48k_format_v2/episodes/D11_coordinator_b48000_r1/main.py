def solve(data):
    totals = {}
    for key, value in data:
        if key in totals:
            totals[key] += value
        else:
            totals[key] = value
    return [[key, totals[key]] for key in sorted(totals)]