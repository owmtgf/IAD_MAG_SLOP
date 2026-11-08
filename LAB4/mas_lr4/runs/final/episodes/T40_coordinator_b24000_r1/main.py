def solve(data):
    used = set()
    out = []
    for job, skill in data['jobs']:
        chosen = None
        for worker in data['workers']:
            if worker['id'] not in used and skill in worker['skills']:
                chosen = worker['id']
                used.add(worker['id'])
                break
        out.append([job, chosen])
    return out