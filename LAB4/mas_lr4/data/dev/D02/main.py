def solve(data):
    amount, threshold, percent = data
    if amount > threshold:
        return amount - amount * percent // 100
    return amount
