def solve(data):
    failed = set(data['failed'])
    # Строим обратный граф: для каждого узла список тех, кто зависит от него
    reverse_deps = {node: [] for node in data['deps']}
    for node, parents in data['deps'].items():
        for p in parents:
            if p in reverse_deps:
                reverse_deps[p].append(node)
    
    # BFS для поиска всех зависимых задач
    affected = set(failed)
    queue = list(failed)
    visited = set(failed)
    
    while queue:
        current = queue.pop(0)
        for dependent in reverse_deps.get(current, []):
            if dependent not in visited:
                visited.add(dependent)
                affected.add(dependent)
                queue.append(dependent)
    
    return sorted(affected - failed)
