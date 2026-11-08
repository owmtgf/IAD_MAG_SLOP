def solve(data):
    failed = set(data['failed'])
    affected = set(failed)
    
    def find_dependents(node):
        # Находим всех узлов, которые зависят от node
        # deps[x] = [p1, p2] -> x зависит от p1 и p2
        # Нам нужно найти x, где node в deps[x]
        result = []
        for x, parents in data['deps'].items():
            if node in parents:
                result.append(x)
        return result
    
    # Используем рекурсию с проверкой visited
    def dfs(node):
        if node in affected:
            return
        for succ in find_dependents(node):
            if succ not in affected:
                affected.add(succ)
                dfs(succ)
    
    for f in failed:
        dfs(f)
    
    return sorted(affected - failed)
