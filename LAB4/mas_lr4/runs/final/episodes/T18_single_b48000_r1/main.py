def solve(data):
    n = len(data)
    if n == 0:
        return []
    adj = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if max(data[i][0], data[j][0]) < min(data[i][1], data[j][1]):
                adj[i].append(j)
                adj[j].append(i)
    visited = [False] * n
    groups = []
    for start in range(n):
        if not visited[start]:
            component = []
            stack = [start]
            visited[start] = True
            while stack:
                u = stack.pop()
                component.append(u)
                for v in adj[u]:
                    if not visited[v]:
                        visited[v] = True
                        stack.append(v)
            groups.append(sorted(component))
    return groups
