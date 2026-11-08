def solve(data):
    failed = set(data['failed'])
    deps = data['deps']
    
    # BFS для поиска всех узлов, зависящих от failed
    # Ребро идет от предшественника к зависимому
    # Если node зависит от p, то p -> node
    # Нам нужно найти всех node, таких что существует путь failed -> ... -> node
    
    affected = set()
    queue = list(failed)
    visited = set(failed)
    
    while queue:
        current = queue.pop(0)
        # Находим всех узлов, у которых current является предшественником
        for node, parents in deps.items():
            if current in parents and node not in visited:
                visited.add(node)
                affected.add(node)
                queue.append(node)
    
    # Результат: все affected, исключая failed, отсортированные по алфавиту
    result = sorted([x for x in affected if x not in failed])
    return result
