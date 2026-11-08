def solve(data):
    failed = set(data['failed'])
    affected = set(failed)
    queue = list(failed)
    visited = set(failed)
    
    while queue:
        current = queue.pop(0)
        for node, parents in data['deps'].items():
            if node in visited:
                continue
            if current in parents:
                affected.add(node)
                visited.add(node)
                queue.append(node)
    
    return sorted(affected - failed)
