def solve(data):
    coupon = data['coupon']
    shipping = data['shipping']
    if coupon['threshold'] < 0 or coupon['amount'] < 0 or shipping['free_threshold'] < 0 or shipping['fee'] < 0:
        raise ValueError('settings')
    lines = []
    for item in data['items']:
        price = item['unit_price']
        quantity = item['quantity']
        discount = item['discount_pct']
        if price < 0 or quantity < 0 or discount < 0 or discount > 100:
            raise ValueError('line')
        reduction = (price * discount + 50) // 100
        lines.append((price - reduction) * quantity)
    subtotal = sum(lines)
    coupon_discount = 0
    if subtotal > coupon['threshold']:
        coupon_discount = min(coupon['amount'], subtotal)
    shipping_cost = 0
    if len(lines) > 0 and subtotal < shipping['free_threshold']:
        shipping_cost = shipping['fee']
    return {'lines': lines, 'subtotal': subtotal, 'coupon_discount': coupon_discount,
            'shipping': shipping_cost, 'total': subtotal-coupon_discount+shipping_cost}
