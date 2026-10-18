def solve(data):
    return [r['id'] for r in data['rows'] if r['active'] and r['score'] > data['minimum']]
