def solve(data):
    n = len(data)
    parent = list(range(n))
    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root
    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry
    for i in range(n):
        for j in range(i + 1, n):
            if max(data[i][0], data[j][0]) < min(data[i][1], data[j][1]):
                union(i, j)
    groups = []
    visited = [False] * n
    for i in range(n):
        if not visited[i]:
            group = []
            stack = [i]
            visited[i] = True
            while stack:
                u = stack.pop()
                group.append(u)
                for v in range(n):
                    if not visited[v] and max(data[u][0], data[v][0]) < min(data[u][1], data[v][1]):
                        visited[v] = True
                        stack.append(v)
            groups.append(sorted(group))
    return groups
