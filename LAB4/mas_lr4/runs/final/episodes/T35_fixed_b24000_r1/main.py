def solve(data):
    budget = data['budget']
    accepted = []
    for job in sorted(data['jobs'],key=lambda j:(j['priority'],j['id'])):
        if job['cost'] <= budget:
            budget -= job['cost']
            accepted.append(job['id'])
    return accepted
