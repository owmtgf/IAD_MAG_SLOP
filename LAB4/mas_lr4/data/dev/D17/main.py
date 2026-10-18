def solve(data):
    for r in data['resources']:
        if r['available'] and data['skill'] in r['skills'] and r['cost'] < data['budget']:
            return r['id']
    return None
