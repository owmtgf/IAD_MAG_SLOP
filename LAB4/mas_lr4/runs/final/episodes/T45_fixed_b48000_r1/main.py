def solve(data):
    failed = set(data['failed'])
    affected = set()
    queue = list(failed)
    while queue:
        node = queue.pop(0)
        if node in affected:
            continue
        affected.add(node)
        if node in data['deps']:
            for child in data['deps'][node]:
                if child not in affected:
                    queue.append(child)
    return sorted(affected - failed)
