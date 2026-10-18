def solve(data):
    point = data['point']
    return any(start <= point <= end for start, end in data['intervals'])
