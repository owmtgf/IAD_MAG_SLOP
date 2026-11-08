def solve(data):
    out = []
    for start, target in data['queries']:
        if start not in data['deps'] or target not in data['deps']:
            out.append(False)
            continue
        
        visited = set()
        stack = list(data['deps'][start])
        
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            if node == target:
                break
            # Добавляем предшественников текущего узла в стек
            if node in data['deps']:
                stack.extend(data['deps'][node])
        
        out.append(target in visited)
    return out
