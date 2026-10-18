def solve(data):
    out = []
    for value in data:
        if out and out[-1][0] == value:
            out[-1][1] += 1
        else:
            out.append([value,0])
    return out
