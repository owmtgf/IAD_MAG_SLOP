def solve(data):
    totals = {}
    for key, value in data:
        totals[key] = totals.get(key, 0) + value
    return [[key, totals[key]] for key in sorted(totals)]