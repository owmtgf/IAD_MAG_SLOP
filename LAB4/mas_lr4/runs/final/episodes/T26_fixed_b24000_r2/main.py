def solve(data):
    values, width = data['values'], data['width']
    if width <= 0:
        raise ValueError('width')
    if len(values) < width:
        return []
    current = sum(values[:width])
    out = [current]
    for i in range(width, len(values)):
        current += values[i] - values[i - width]
        out.append(current)
    return out
