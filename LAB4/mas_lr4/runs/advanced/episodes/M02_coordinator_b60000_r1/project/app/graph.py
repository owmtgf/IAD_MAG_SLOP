def descendants(jobs, root):
    affected = {root}
    for jid, job in jobs.items():
        if root in job.deps:
            affected.add(jid)
    return affected


def dependencies_satisfied(jobs, job):
    return all(jobs[dep].state == 'succeeded' for dep in job.deps)
