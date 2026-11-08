def solve(data):
    failed = set(data['failed'])
    affected = set(failed)
    changed = True
    while changed:
        changed = False
        for node, parents in data['deps'].items():
            if node not in affected:
                if len(parents) > 0 and all(p in affected for p in parents):
                    affected.add(node)
                    changed = True
    return sorted(affected - failed)
