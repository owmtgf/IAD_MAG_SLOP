def solve(data):
    old,new = data['old'],data['new']
    return {
        'added': sorted(k for k in new if k not in old),
        'removed': sorted(k for k in old if k not in new),
        'changed': sorted(k for k in old if k in new and old[k] != new[k])
    }
