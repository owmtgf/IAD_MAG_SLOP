def solve(data):
    seen = set()
    payments = {}
    for event in data['events']:
        ident = event['id']
        event_tuple = (event['kind'], event['amount'], event['payment'] if event['kind'] == 'refund' else None)
        if ident in seen:
            continue
        if event_tuple in seen:
            continue
        seen.add(ident)
        seen.add(event_tuple)
        amount = event['amount']
        if amount <= 0:
            raise ValueError('amount')
        if event['kind'] == 'pay':
            payments[ident] = [amount, 0]
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
        rows.append({'id': ident, 'paid': paid, 'refunded': returned, 'remaining': paid-returned})
    rows.sort(key=lambda x: x['id'])
    return {'balance': sum(row['remaining'] for row in rows), 'payments': rows}
