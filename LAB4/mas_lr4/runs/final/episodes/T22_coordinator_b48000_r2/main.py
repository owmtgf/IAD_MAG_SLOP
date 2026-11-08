def solve(data):
    chosen = {}
    for idx, row in enumerate(data):
        key = row['id']
        if key not in chosen or row['time'] > chosen[key]['time'] or (row['time'] == chosen[key]['time'] and idx > chosen[key]['idx']):
            chosen[key] = dict(row)
            chosen[key]['idx'] = idx
    return [chosen[key] for key in sorted(chosen)]