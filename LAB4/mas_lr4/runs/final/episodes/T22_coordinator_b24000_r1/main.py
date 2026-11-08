def solve(data):
    chosen = {}
    for row in data:
        key = row['id']
        if key not in chosen or row['time'] > chosen[key]['time']:
            chosen[key] = dict(row)
    return [chosen[key] for key in sorted(chosen)]
