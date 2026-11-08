def solve(data):
    remaining = []
    bins = []
    for size in data['sizes']:
        target = next((i for i, r in enumerate(remaining) if r > size), len(remaining))
        if target == len(remaining):
            remaining.append(data['capacity'])
        remaining[target] -= size
        bins.append(target)
    return {'bins': bins, 'remaining': remaining}
