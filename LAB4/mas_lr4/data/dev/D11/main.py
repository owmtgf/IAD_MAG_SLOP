def solve(data):
    totals = {}
    for key,value in data:
        totals[key] = value
    return [[key,totals[key]] for key in sorted(totals)]
