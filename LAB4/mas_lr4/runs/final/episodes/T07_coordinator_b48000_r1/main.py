def solve(data):
    total = 0
    for amount, numerator, denominator in data:
        scaled = amount * numerator
        remainder = scaled % denominator
        if remainder * 2 >= denominator:
            total += (scaled // denominator) + 1
        else:
            total += (scaled // denominator)
    return total
