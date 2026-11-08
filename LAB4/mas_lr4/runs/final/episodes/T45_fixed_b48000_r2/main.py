def solve(data):
    failed = set(data['failed'])
    affected = set(failed)
    queue = list(failed)
    while queue:
        node = queue.pop(0)
        if node in data['deps']:
            for child in data['deps'][node]:
                if child not in affected:
                    affected.add(child)
                    queue.append(child)
    return sorted(affected - failed)
