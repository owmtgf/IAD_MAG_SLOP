def solve(data):
    out = []
    for row in data:
        free = row['on_hand'] - row['reserved']
        if free < row['minimum']:
            quantity = row['target'] - free
        else:
            quantity = 0
        out.append([row['id'], quantity])
    return out