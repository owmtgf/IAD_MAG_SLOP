def solve(data):
    out = []
    for start, target in data['queries']:
        # Если start или target не существуют в deps, ответ False
        if start not in data['deps'] or target not in data['deps']:
            out.append(False)
            continue
        
        # Если start == target, проверяем, существует ли такой id (он есть, так как проверили выше)
        if start == target:
            out.append(True)
            continue
        
        # Нужно проверить, может ли target достичь start через ребра.
        # Ребра идут от предшественника к зависимому: pred -> node.
        # Значит, чтобы проверить, может ли target достичь start, нужно идти по ребрам от target.
        seen = set()
        stack = list(data['deps'][target])
        while stack:
            node = stack.pop()
            if node not in seen:
                seen.add(node)
                # Добавляем предшественники node (ребра node -> pred)
                stack.extend(data['deps'].get(node, []))
        
        out.append(start in seen)
    return out