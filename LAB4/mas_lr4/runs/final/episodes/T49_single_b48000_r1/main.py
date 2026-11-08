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
        result = []
        for p in unique:
            is_redundant = False
            for q in unique:
                if p != q and reaches(p, q):
                    is_redundant = True
                    break
            if not is_redundant:
                result.append(p)
        out[node] = result
    return out
