def solve(data):
    pieces = []
    for a,b in data['a']:
        for c,d in data['b']:
            left, right = max(a,c), min(b,d)
            if left <= right:
                pieces.append([left,right])
    out = []
    for left,right in sorted(pieces):
        if out and left <= out[-1][1]:
            out[-1][1] = max(out[-1][1],right)
        else:
            out.append([left,right])
    return out
