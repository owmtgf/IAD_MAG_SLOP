def solve(data):
    total = 0
    for amount, numerator, denominator in data:
        # Округление половины вверх: floor(x + 0.5)
        # x = amount * numerator / denominator
        # floor(x + 0.5) = (amount * numerator * 2 + denominator) // (2 * denominator)
        scaled = amount * numerator * 2 + denominator
        total += scaled // (2 * denominator)
    return total
