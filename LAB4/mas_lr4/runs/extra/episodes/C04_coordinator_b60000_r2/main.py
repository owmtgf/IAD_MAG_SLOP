def solve(data):
    dependencies = data['dependencies']
    nodes = set(dependencies.keys())
    
    # Проверка: каждый id в changed и cached должен быть ключом dependencies
    for node in data['changed'] + data['cached']:
        if node not in nodes:
            raise ValueError('node')
    
    # Проверка: все ссылки в значениях dependencies должны быть ключами
    for req_list in dependencies.values():
        for req in req_list:
            if req not in nodes:
                raise ValueError('dependency')
    
    # Если changed пустой, ничего не инвалидируется
    if not data['changed']:
        return {'invalidated': [], 'remaining': sorted(data['cached'])}
    
    # Инициализация: affected = changed
    affected = set(data['changed'])
    
    # Поиск всех объектов, от которых зависит хотя бы один из affected
    # Если node в dependencies[req], то req зависит от node
    # Если node изменен, то req должен быть добавлен в affected
    # Алгоритм: пока есть node в affected, ищем все req, где node в dependencies[req]
    
    changed_to_check = set(data['changed'])
    
    while changed_to_check:
        node = changed_to_check.pop()
        # Находим все требования, от которых зависит node
        # То есть node в dependencies[requirement]
        for req in nodes:
            if node in dependencies[req]:
                if req not in affected:
                    affected.add(req)
                    changed_to_check.add(req)
    
    # Фильтрация: invalidated = cached & affected
    invalidated = affected.intersection(set(data['cached']))
    remaining = set(data['cached']) - affected
    
    return {
        'invalidated': sorted(invalidated),
        'remaining': sorted(remaining)
    }