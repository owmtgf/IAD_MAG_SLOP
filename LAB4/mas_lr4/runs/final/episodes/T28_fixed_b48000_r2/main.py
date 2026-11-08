def solve(data):
    old, new = data['old'], data['new']
    added = []
    removed = []
    changed = []
    
    for k in new:
        if k not in old:
            added.append(k)
    
    for k in old:
        if k not in new:
            removed.append(k)
        else:
            if old[k] != new[k]:
                changed.append(k)
    
    return {
        'added': sorted(added),
        'removed': sorted(removed),
        'changed': sorted(changed)
    }