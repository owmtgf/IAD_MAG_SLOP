def solve(data):
    total = 0
    for amount, numerator, denominator in data:
        # Пересчёт: amount * (numerator / denominator)
        # Округление половины вверх до целой копейки
        # Формула: floor(x + 0.5) для положительного x
        # Для x = amount * numerator / denominator
        # Вычисляем: floor((amount * numerator * 2 + denominator) / (2 * denominator))
        # Но проще: (amount * numerator + denominator // 2) // denominator
        # Проверка: 1/2 -> (1 + 1)//2 = 1 (верно)
        # 3/2 -> (3 + 1)//2 = 2 (верно)
        # 1/3 -> (1 + 1)//3 = 0 (верно)
        # 2/3 -> (2 + 1)//3 = 1 (верно)
        # 100*3/2 = 150 -> (300 + 1)//2 = 150 (верно)
        # 0*3/2 = 0 -> (0 + 1)//2 = 0 (верно)
        # 99*0/7 = 0 -> (0 + 3)//7 = 0 (верно)
        # 7*2/3 + 5*3/2 = 4 + 7 = 11? Нет, 14/3=4.66->5, 15/2=7.5->8, 5+8=13. Верно.
        # Формула: (amount * numerator + denominator // 2) // denominator
        term = amount * numerator
        rounded = (term + denominator // 2) // denominator
        total += rounded
    return total
