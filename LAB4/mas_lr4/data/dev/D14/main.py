def solve(data):
    rows = sorted(data['rows'],key=lambda row:row[1])
    return [r[0] for r in rows[:data['k']]]
