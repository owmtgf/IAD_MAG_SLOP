def solve(data):
    index = {}
    for key, value in data['right']:
        index.setdefault(key, []).append(value)
    out = []
    for key, value in data['left']:
        matches = index.get(key, [])
        if not matches:
            out.append([key, value, None])
        else:
            for other in matches:
                out.append([key, value, other])
    return out
