def solve(data):
    color = {}
    def visit(node):
        if node not in data:
            return False
        if color.get(node, 0) == 1:
            return True
        if color.get(node, 0) == 2:
            return False
        color[node] = 1
        for parent in data[node]:
            if visit(parent):
                return True
        color[node] = 2
        return False
    return any(visit(node) for node in data)
