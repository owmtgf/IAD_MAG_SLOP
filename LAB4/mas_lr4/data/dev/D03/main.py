def solve(data):
    amount, threshold, fee = data
    if amount > threshold:
        return 0
    return fee
