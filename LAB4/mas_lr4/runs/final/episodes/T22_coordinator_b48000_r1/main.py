def solve(data):
    chosen = {}
    for i, row in enumerate(data):
        key = row['id']
        if key not in chosen:
            chosen[key] = row
        elif row['time'] > chosen[key]['time'] or (row['time'] == chosen[key]['time'] and i > chosen[key]['index']):
            chosen[key] = row
            chosen[key]['index'] = i
    result = []
    for key in sorted(chosen):
        result.append({k: v for k, v in chosen[key].items() if k != 'index'})
    return result