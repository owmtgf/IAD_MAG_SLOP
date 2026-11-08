def solve(data):
    out = {}
    for line in data:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise ValueError('separator')
        parts = line.split('=', 1)
        if len(parts) != 2:
            raise ValueError('separator')
        key, value = parts[0].strip(), parts[1].strip()
        if not key or key in out:
            raise ValueError('key')
        out[key] = value
    return out
