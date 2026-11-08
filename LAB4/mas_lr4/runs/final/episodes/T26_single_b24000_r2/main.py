def solve(data):
    values, width = data['values'], data['width']
    if width <= 0:
        raise ValueError('width')
    if len(values) < width:
        return []
    out = []
    current = sum(values[:width])
    out.append(current)
    for i in range(width, len(values)):
        current = current - values[i - width] + values[i]
        out.append(current)
    return out
