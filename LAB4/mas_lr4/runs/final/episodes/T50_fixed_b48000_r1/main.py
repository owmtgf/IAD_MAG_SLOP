def solve(data):
    out = []
    for start, target in data['queries']:
        if start not in data['deps'] or target not in data['deps']:
            out.append(False)
            continue
        if start == target:
            out.append(True)
            continue
        # Проверка: может ли target достичь start?
        # Граф: u -> v если v в deps[u]
        # Нужно найти все узлы, достижимые из target
        seen = set()
        stack = [target]
        while stack:
            node = stack.pop()
            if node not in seen:
                seen.add(node)
                # Добавляем прямых предшественников node
                for pred in data['deps'].get(node, []):
                    if pred not in seen:
                        stack.append(pred)
        out.append(start in seen)
    return out