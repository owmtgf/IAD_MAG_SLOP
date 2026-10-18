def solve(data):
    dependencies = data['dependencies']
    nodes = set(dependencies)
    for requirements in dependencies.values():
        for requirement in requirements:
            if requirement not in nodes:
                raise ValueError('dependency')
    for node in data['changed'] + data['cached']:
        if node not in nodes:
            raise ValueError('node')
    affected = set(data['changed'])
    pending = list(data['changed'])
    while pending:
        node = pending.pop()
        for requirement in dependencies[node]:
            if requirement not in affected:
                affected.add(requirement)
                pending.append(requirement)
    cached = set(data['cached'])
    return {'invalidated': sorted(cached.intersection(affected)),
            'remaining': sorted(cached.difference(affected))}
