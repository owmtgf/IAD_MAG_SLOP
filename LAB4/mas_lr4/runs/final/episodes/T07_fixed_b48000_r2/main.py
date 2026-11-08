def solve(data):
    total = 0
    for amount, numerator, denominator in data:
        # Округление половины вверх: (числитель * количество + знаменатель - 1) // знаменатель
        # Это эквивалентно ceil(amount * numerator / denominator)
        total += (amount * numerator + denominator - 1) // denominator
    return total