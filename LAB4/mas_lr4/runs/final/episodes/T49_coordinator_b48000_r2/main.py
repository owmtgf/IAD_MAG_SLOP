def solve(data):
    def reaches(start, target):
        stack = [start]
        seen = set()
        while stack:
            node = stack.pop()
            if node == target:
                return True
            if node not in seen:
                seen.add(node)
                stack.extend(data[node])
        return False
    out = {}
    for node, parents in data.items():
        unique = sorted(set(parents))
        filtered = []
        for p in unique:
            if not any(reaches(p, q) for q in unique if q != p):
                filtered.append(p)
        out[node] = filtered
    return out
