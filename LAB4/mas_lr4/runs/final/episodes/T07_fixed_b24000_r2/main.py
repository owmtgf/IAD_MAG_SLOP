def solve(data):
    total = 0
    for amount, numerator, denominator in data:
        scaled = amount * denominator
        total += round(scaled / denominator)
    return total
