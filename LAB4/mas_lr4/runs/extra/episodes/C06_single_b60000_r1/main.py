def solve(data):
    lines = list(data['lines'])
    gross = 0
    basis = 0
    for line in lines:
        value = line['price'] * line['qty']
        gross += value
        if line['eligible']:
            basis += value
    discount = 0
    if gross > data['coupon']['minimum']:
        discount = min(data['coupon']['amount'], gross)
    allocated = {line['id']: 0 for line in lines}
    if basis:
        for line in lines:
            if line['eligible']:
                allocated[line['id']] = discount * line['price'] * line['qty'] // basis
        left = discount - sum(allocated.values())
        for line in lines:
            if left and line['eligible']:
                allocated[line['id']] += 1
                left -= 1
    lookup = {line['id']: line for line in lines}
    returned = {line['id']: 0 for line in lines}
    refunded = {line['id']: 0 for line in lines}
    refunds = []
    for event in data['returns']:
        ident = event['id']
        line = lookup[ident]
        qty = min(event['qty'], line['qty'] - returned[ident])
        if qty <= 0:
            refunds.append({'accepted': False, 'amount': 0})
            continue
        unit_discount = allocated[ident] // line['qty']
        amount = qty * (line['price'] - unit_discount)
        returned[ident] += qty
        refunded[ident] += amount
        refunds.append({'accepted': True, 'amount': amount})
    shipping = data['shipping']['fee']
    if gross >= data['shipping']['free_at']:
        shipping = 0
    total_refund = sum(refunded.values())
    result = []
    for line in lines:
        ident = line['id']
        remaining_qty = line['qty'] - returned[ident]
        unit_paid = line['price'] - allocated[ident] // line['qty']
        result.append({
            'id': ident,
            'discount': allocated[ident],
            'returned_qty': returned[ident],
            'refunded': refunded[ident],
            'remaining': remaining_qty * unit_paid
        })
    charged = gross - discount + shipping
    return {
        'gross': gross,
        'discount': discount,
        'shipping': shipping,
        'charged': charged,
        'refunds': refunds,
        'refunded': total_refund,
        'balance': charged - total_refund,
        'lines': result
    }
