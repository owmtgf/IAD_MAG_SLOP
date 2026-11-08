def solve(data):
    paid, quantity, returned = data['paid'], data['quantity'], data['returned']
    base = paid // quantity
    extra = paid % quantity
    # Количество единиц, которые получают +1 к стоимости (получают остаток)
    units_with_extra = extra
    # Стоимость первой единицы (с учетом остатка, если она попадает в первые 'units_with_extra')
    unit_price = base + (1 if returned > units_with_extra else 0)
    # Стоимость остальных единиц
    other_price = base
    # Сумма: (количество единиц с остатком) * (base + 1) + (остальные) * base
    # Но нужно быть осторожным: если returned <= units_with_extra, то все returned имеют цену base+1
    # Если returned > units_with_extra, то первые units_with_extra имеют цену base+1, остальные (returned - units_with_extra) имеют цену base
    
    if returned <= units_with_extra:
        return (base + 1) * returned
    else:
        return (base + 1) * units_with_extra + base * (returned - units_with_extra)
