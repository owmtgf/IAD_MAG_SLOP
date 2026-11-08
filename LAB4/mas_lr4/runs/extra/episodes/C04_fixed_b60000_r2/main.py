def solve(data):
    dependencies = data['dependencies']
    nodes = set(dependencies.keys())
    for key in nodes:
        for req in dependencies[key]:
            if req not in nodes:
                raise ValueError('dependency')
    for node in data['changed'] + data['cached']:
        if node not in nodes:
            raise ValueError('node')
    affected = set(data['changed'])
    pending = list(data['changed'])
    while pending:
        node = pending.pop()
        for other, reqs in dependencies.items():
            if node in reqs and other not in affected:
                affected.add(other)
                pending.append(other)
    cached = set(data['cached'])
    return {'invalidated': sorted(cached.intersection(affected)),
            'remaining': sorted(cached.difference(affected))}
