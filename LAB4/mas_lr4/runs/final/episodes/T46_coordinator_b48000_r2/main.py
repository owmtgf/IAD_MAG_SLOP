def solve(data):
    affected = set(data['changed'])
    growing = True
    while growing:
        growing = False
        for node, parents in data['deps'].items():
            if node not in affected and any(p in affected for p in parents):
                affected.add(node)
                growing = True
        # Проверяем потомков: если node в affected, то все child, у которых node в parents, тоже должны быть в affected
        for child, child_parents in data['deps'].items():
            if child in affected:
                for parent in child_parents:
                    if parent in affected:
                        continue
                    # parent уже в affected, значит child должен быть добавлен, если он не там
                    # Но мы ищем потомков. Если child в affected, то его предшественники тоже должны быть обработаны?
                    # Нет, логика: если child в affected, значит он должен быть перезапущен. Его предшественники тоже должны быть перезапущены, если они не в affected.
                    # Но мы уже проходим по всем node. Проблема в том, что мы не добавляем потомков, если они не прямые дети в цикле.
                    # Правильная логика: если node в affected, то все child, у которых node в parents, должны быть добавлены в affected, если они не там.
                    # Но мы уже добавили node в affected. Теперь нужно добавить его потомков.
                    # child_parents содержит предшественников child. Если node в child_parents, то node - предшественник child.
                    # Значит child - потомок node. Если child не в affected, добавляем.
                    if node in child_parents:
                        if child not in affected:
                            affected.add(child)
                            growing = True
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