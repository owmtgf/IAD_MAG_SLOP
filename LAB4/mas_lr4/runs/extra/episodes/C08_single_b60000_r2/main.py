def solve(data):
    jobs = {job['id']: job for job in data['jobs']}
    names = sorted(jobs)
    tenants = sorted(set(job['tenant'] for job in jobs.values()))
    status = {name: 'pending' for name in names}
    attempts = {name: 0 for name in names}
    ready = {name: jobs[name]['release'] for name in names}
    slots = [None for i in range(data['slots'])]
    starts = []
    for now in range(data['horizon']):
        for slot in range(len(slots)):
            running = slots[slot]
            if running is None or running['finish'] > now:
                continue
            name = running['id']
            job = jobs[name]
            attempt = attempts[name]
            if job['outcomes'][attempt - 1]:
                status[name] = 'succeeded'
            elif attempt == len(job['outcomes']):
                status[name] = 'failed'
            else:
                status[name] = 'pending'
                ready[name] = running['started'] + job['backoff']
            slots[slot] = None
        for name in names:
            if status[name] != 'pending' or ready[name] > now:
                continue
            if any(status[parent] == 'failed' for parent in jobs[name]['deps']):
                status[name] = 'blocked'
        cursor = 0
        for slot in range(len(slots)):
            if slots[slot] is not None:
                continue
            available = []
            for offset in range(len(tenants)):
                index = (cursor + offset) % len(tenants)
                tenant = tenants[index]
                for name in names:
                    job = jobs[name]
                    if job['tenant'] != tenant:
                        continue
                    if status[name] != 'pending' or ready[name] > now:
                        continue
                    if not all(status[parent] in ['succeeded', 'blocked'] for parent in job['deps']):
                        continue
                    available.append(name)
                if available:
                    break
            if not available:
                continue
            available.sort(key=lambda name: (-jobs[name]['priority'], name))
            chosen = available[0]
            job = jobs[chosen]
            attempts[chosen] += 1
            status[chosen] = 'running'
            slots[slot] = {
                'id': chosen,
                'started': now,
                'finish': now + job['duration']
            }
            cursor = index
            starts.append({
                'time': now,
                'slot': slot,
                'id': chosen,
                'attempt': attempts[chosen]
            })
    result = []
    for name in names:
        result.append({'id': name, 'status': status[name], 'attempts': attempts[name]})
    running = []
    for slot in range(len(slots)):
        current = slots[slot]
        if current is not None:
            running.append({'slot': slot, 'id': current['id'], 'finish': current['finish']})
    return {'starts': starts, 'jobs': result, 'running': running}
