def solve(data):
    free = dict(data['stock'])
    shipped = {sku: 0 for sku in free}
    reservations = {}
    log = []
    for event in data['events']:
        for hold in reservations.values():
            if hold['status'] == 'active' and hold['expires'] < event['t']:
                hold['status'] = 'expired'
                for sku, qty in hold['left'].items():
                    free[sku] += qty
                    hold['left'][sku] = 0
        op = event['op']
        if op == 'restock':
            for sku, qty in event['items'].items():
                free[sku] += qty
            log.append('restocked')
            continue
        ident = event['id']
        if op == 'reserve':
            old = reservations.get(ident)
            if old is not None and old['status'] == 'active':
                log.append('duplicate')
                continue
            possible = True
            for sku, qty in event['items'].items():
                if qty > free[sku]:
                    possible = False
                else:
                    free[sku] -= qty
            if not possible:
                log.append('insufficient')
                continue
            reservations[ident] = {'status': 'active', 'expires': event['expires'], 'left': dict(event['items'])}
            log.append('reserved')
            continue
        hold = reservations.get(ident)
        if hold is None or hold['status'] != 'active':
            log.append('inactive')
            continue
        if op == 'cancel':
            hold['status'] = 'cancelled'
            for sku, qty in hold['left'].items():
                free[sku] += qty
                hold['left'][sku] = 0
            log.append('cancelled')
            continue
        possible = True
        for sku, qty in event['items'].items():
            if qty > hold['left'].get(sku, 0):
                possible = False
        if not possible:
            log.append('exceeds')
            continue
        for sku, qty in event['items'].items():
            hold['left'][sku] -= qty
            shipped[sku] += qty
            free[sku] += qty
        if any(qty == 0 for qty in hold['left'].values()):
            hold['status'] = 'completed'
        log.append('fulfilled')
    result = []
    for ident in sorted(reservations):
        hold = reservations[ident]
        left = hold['left'] if hold['status'] == 'active' else {sku: 0 for sku in hold['left']}
        result.append({'id': ident, 'status': hold['status'], 'remaining': dict(left)})
    inventory = []
    for sku in sorted(free):
        held = sum(h['left'].get(sku, 0) for h in reservations.values() if h['status'] == 'active')
        inventory.append({'sku': sku, 'available': free[sku], 'reserved': held, 'shipped': shipped[sku]})
    return {'log': log, 'inventory': inventory, 'reservations': result}
