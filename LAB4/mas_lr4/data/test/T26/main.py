def solve(data):
    values,width = data['values'],data['width']
    if width <= 0:
        raise ValueError('width')
    if len(values) < width:
        return []
    current = sum(values[:width])
    out = []
    for i in range(width,len(values)):
        current += values[i]
        out.append(current)
    return out
