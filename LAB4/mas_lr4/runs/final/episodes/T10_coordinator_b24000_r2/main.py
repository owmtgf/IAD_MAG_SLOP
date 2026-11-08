def solve(data):
    debts = data['debts']
    n = len(debts)
    if n == 0:
        return []
    
    # Создаем индексы и сортируем их по (due, id)
    indices = list(range(n))
    indices.sort(key=lambda i: (debts[i]['due'], debts[i]['id']))
    
    budget = data['budget']
    result = [0] * n
    
    for idx in indices:
        if budget <= 0:
            break
        
        amount = debts[idx]['amount']
        if amount == 0:
            result[idx] = 0
            continue
        
        pay = min(budget, amount)
        result[idx] = pay
        budget -= pay
    
    # Возвращаем результат в исходном порядке
    return [[debts[i]['id'], result[i]] for i in range(n)]
