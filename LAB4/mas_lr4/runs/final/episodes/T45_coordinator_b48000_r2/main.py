def solve(data):
    failed = set(data['failed'])
    affected = set()
    queue = list(failed)
    visited = set(failed)
    
    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        affected.add(node)
        
        # Найти все задачи, у которых 'node' является предшественником
        # Это означает, что 'node' входит в список deps[target]
        for target, predecessors in data['deps'].items():
            if target not in visited and node in predecessors:
                queue.append(target)
    
    return sorted(affected - failed)
