def solve(data):
    affected = set(data['changed'])
    changed_set = set(affected)
    
    # Рекурсивное добавление всех потомков в affected
    # Используем стек для итеративной рекурсии
    stack = list(changed_set)
    while stack:
        node = stack.pop()
        if node in data['deps']:
            for child in data['deps'][node]:
                if child not in affected:
                    affected.add(child)
                    stack.append(child)
    
    out = []
    done = set()
    while affected:
        candidates = [k for k in affected if all(p in done for p in data['deps'].get(k, []))]
        if not candidates:
            break
        node = min(candidates)
        out.append(node)
        done.add(node)
        affected.remove(node)
    return out