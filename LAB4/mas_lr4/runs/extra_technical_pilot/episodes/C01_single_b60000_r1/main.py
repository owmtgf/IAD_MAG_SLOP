def solve(data):
    seen = set()
    events_order = []
    for event in data['events']:
        ident = event['id']
        if ident in seen:
            continue
        seen.add(ident)
        events_order.append(event)
    
    payments = {}
    for event in events_order:
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
    for ident in sorted(payments.keys()):
        paid, returned = payments[ident]
        rows.append({'id': ident, 'paid': paid, 'refunded': returned, 'remaining': paid - returned})
    
    return {'balance': sum(row['remaining'] for row in rows), 'payments': rows}
