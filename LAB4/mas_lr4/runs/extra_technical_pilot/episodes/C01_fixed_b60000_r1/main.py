def solve(data):
    seen = set()
    payments = {}
    for event in data['events']:
        # Проверка на дубликат по полному содержимому события
        event_key = (event['id'], event['kind'], event['amount'], event.get('payment'))
        if event_key in seen:
            continue
        seen.add(event_key)
        
        amount = event['amount']
        if amount <= 0:
            raise ValueError('amount')
        
        if event['kind'] == 'pay':
            payments[event['id']] = [amount, 0]
        else:
            target = event['payment']
            if target not in payments:
                raise ValueError('payment')
            if amount > payments[target][0]:
                raise ValueError('refund')
            payments[target][1] = amount
    
    rows = []
    for ident in payments:
        paid, returned = payments[ident]
        rows.append({'id': ident, 'paid': paid, 'refunded': returned, 'remaining': paid - returned})
    
    # Сортировка по id лексикографически
    rows.sort(key=lambda x: x['id'])
    
    return {'balance': sum(row['remaining'] for row in rows), 'payments': rows}
