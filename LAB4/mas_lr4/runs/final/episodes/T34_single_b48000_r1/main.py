def solve(data):
    remaining = []
    bins = []
    for size in data['sizes']:
        target = -1
        for i in range(len(remaining)):
            if remaining[i] > size:
                target = i
                break
        if target == -1:
            target = len(remaining)
            remaining.append(data['capacity'])
        remaining[target] -= size
        bins.append(target)
    return {'bins':bins,'remaining':remaining}
