def solve(data):
    seen = set()
    groups = []
    for first in range(len(data)):
        if first in seen:
            continue
        stack = [first]
        seen.add(first)
        group = []
        while stack:
            i = stack.pop()
            group.append(i)
            for j in range(len(data)):
                if j not in seen:
                    start_i, end_i = data[i]
                    start_j, end_j = data[j]
                    if max(start_i, start_j) < min(end_i, end_j):
                        seen.add(j)
                        stack.append(j)
        groups.append(sorted(group))
    return groups
