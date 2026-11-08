def solve(data):
    affected = set(data['changed'])
    growing = True
    while growing:
        growing = False
        for node, parents in data['deps'].items():
            if node not in affected and any(p in affected for p in parents):
                affected.add(node)
                growing = True
    out = []
    done = set()
    while affected:
        candidates = []
        for k in affected:
            if k in data['deps']:
                if all(p in done for p in data['deps'][k]):
                    candidates.append(k)
            else:
                # Узел в affected, но не в deps (листок или ошибка логики, но по условию все ссылки существуют)
                # Если узел не в deps, у него нет предшественников, значит он готов к выполнению
                candidates.append(k)
        if not candidates:
            break
        node = min(candidates)
        out.append(node)
        done.add(node)
        affected.remove(node)
    return out
