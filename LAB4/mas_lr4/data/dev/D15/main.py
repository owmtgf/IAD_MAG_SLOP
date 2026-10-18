def solve(data):
    out = data['base']
    for key,value in data['patch'].items():
        if value is None:
            out.pop(key,None)
        else:
            out[key] = value
    return out
