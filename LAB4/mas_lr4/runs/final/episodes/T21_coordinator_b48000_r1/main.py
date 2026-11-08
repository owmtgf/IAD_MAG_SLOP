def solve(data):
    index = {}
    for key,value in data['right']:
        index.setdefault(key,[]).append(value)
    out = []
    for key,value in data['left']:
        matches = index.get(key,[])
        if matches:
            for other in matches:
                out.append([key,value,other])
        else:
            out.append([key,value,None])
    return out
