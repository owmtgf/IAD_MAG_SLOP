def solve(data):
    rows = data['rows']
    minimum = data['minimum']
    offset = data['offset']
    limit = data['limit']
    
    filtered = []
    for r in rows:
        if r[1] >= minimum:
            filtered.append(r)
    
    filtered.sort(key=lambda r: (-r[1], r[0]))
    
    result = []
    start = offset
    end = offset + limit
    
    for i in range(start, end):
        if i < len(filtered):
            result.append(filtered[i][0])
    
    return result