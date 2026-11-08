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
        to_remove = []
        for p in unique:
            # Удаляем p, если существует другой q в unique, такой что q может достичь p
            # (т.е. p избычен, так как путь к p идет через q)
            is_redundant = False
            for q in unique:
                if p != q and reaches(q, p):
                    is_redundant = True
                    break
            if is_redundant:
                to_remove.append(p)
        out[node] = [p for p in unique if p not in to_remove]
    return out
