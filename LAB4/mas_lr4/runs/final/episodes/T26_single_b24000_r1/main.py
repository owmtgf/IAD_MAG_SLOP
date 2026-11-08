def solve(data):
    values, width = data['values'], data['width']
    if width <= 0:
        raise ValueError('width')
    if len(values) < width:
        return []
    out = []
    for i in range(len(values) - width + 1):
        window = values[i:i + width]
        out.append(sum(window))
    return out
