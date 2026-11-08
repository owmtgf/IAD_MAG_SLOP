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
    if not data['changed']:
        return {'invalidated': [], 'remaining': sorted(data['cached'])}
    affected = set(data['changed'])
    pending = list(data['changed'])
    while pending:
        node = pending.pop()
        for dependent in dependencies.get(node, []):
            if dependent not in affected:
                affected.add(dependent)
                pending.append(dependent)
    cached = set(data['cached'])
    return {'invalidated': sorted(cached.intersection(affected)),
            'remaining': sorted(cached.difference(affected))}
