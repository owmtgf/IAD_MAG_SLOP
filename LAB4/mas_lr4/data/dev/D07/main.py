def solve(data):
    out = []
    for start, end in sorted(data):
        if start == end:
            continue
        if out and start < out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out
