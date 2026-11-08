def solve(data):
    if not data.startswith('/'):
        raise ValueError('absolute path required')
    parts = []
    for part in data.split('/'):
        if part == '':
            continue
        if part == '..':
            if not parts:
                raise ValueError('above root')
            parts.pop()
        elif part == '.':
            continue
        else:
            parts.append(part)
    return '/' + '/'.join(parts)
