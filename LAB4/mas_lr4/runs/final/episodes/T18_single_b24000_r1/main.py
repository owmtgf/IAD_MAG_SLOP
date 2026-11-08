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
                    # Проверка на пересечение положительной длины: max(start1, start2) < min(end1, end2)
                    if max(data[i][0], data[j][0]) < min(data[i][1], data[j][1]):
                        seen.add(j)
                        group.append(j)
        groups.append(sorted(group))
    return groups
