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
    
    nodes = sorted(data.keys())
    out = {}
    for node in nodes:
        parents = data[node]
        unique = sorted(set(parents))
        to_remove = []
        for p in unique:
            if any(reaches(p, q) for q in unique if q != p):
                to_remove.append(p)
        out[node] = [p for p in unique if p not in to_remove]
    return out