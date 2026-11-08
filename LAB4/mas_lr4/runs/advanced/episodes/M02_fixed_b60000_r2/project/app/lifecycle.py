def start(runtime, job):
    job.state, job.ticket = 'running', None
    job.attempts += 1
    job.remaining = job.duration
    job.dep_versions = {d: runtime.jobs[d].version for d in sorted(job.deps)}
    runtime.history.append(dict(t=runtime.time, kind='start', id=job.id,
                                version=job.version, attempt=job.attempts))


def finish(runtime, job):
    runtime.locks.release(job.id)
    if job.attempts <= job.failures:
        retry = job.attempts < job.max_retries
        job.state = 'blocked' if retry else 'failed'
        job.dep_versions = {}
        kind = 'retry' if retry else 'failed'
    else:
        job.state, job.completed_at = 'succeeded', runtime.time
        kind = 'succeeded'
    runtime.history.append(dict(t=runtime.time, kind=kind, id=job.id,
                                version=job.version, attempt=job.attempts))
