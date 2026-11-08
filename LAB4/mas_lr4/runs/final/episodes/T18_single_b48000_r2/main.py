def solve(data):
    seen = set()
    groups = []
    for first in range(len(data)):
        if first in seen:
            continue
        queue = [first]
        seen.add(first)
        group = []
        while queue:
            i = queue.pop(0)
            group.append(i)
            for j in range(len(data)):
                if j not in seen:
                    if max(data[i][0], data[j][0]) < min(data[i][1], data[j][1]):
                        seen.add(j)
                        queue.append(j)
        groups.append(sorted(group))
    return groups
