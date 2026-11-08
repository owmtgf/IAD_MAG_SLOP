def solve(data):
    out = []
    for row in data:
        free = row['on_hand'] - row['reserved']
        quantity = row['target'] - free if free <= row['minimum'] else 0
        out.append([row['id'], quantity])
    return out