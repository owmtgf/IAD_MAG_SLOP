def solve(data):
    rows = [r for r in data['rows'] if r[1] >= data['minimum']]
    rows = sorted(rows, key=lambda r: -r[1])
    return [r[0] for r in rows[data['offset']:data['limit']]}