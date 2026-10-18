from copy import deepcopy
from .model import load_jobs
from .graph import descendants, dependencies_satisfied
from .locks import ResourceLocks
from .ordering import ready_order
from .lifecycle import start, finish


class Scheduler:
    def __init__(self, rows):
        self.jobs = load_jobs(rows)
        self.time = self.next_ticket = 0
        self.locks = ResourceLocks()
        self.history, self.errors, self.checkpoints = [], [], {}
        self.dispatch()

    def dispatch(self):
        for jid in sorted(self.jobs):
            job = self.jobs[jid]
            if job.state == 'blocked' and dependencies_satisfied(self.jobs, job):
                job.state, job.ticket = 'ready', self.next_ticket
                self.next_ticket += 1
        reserved = set()
        for job in ready_order(self.jobs):
            if self.locks.acquire(job, reserved):
                start(self, job)
            else:
                self.locks.reserve_waiter(job, reserved)

    def tick(self):
        self.time += 1
        done = []
        for jid in sorted(self.jobs):
            job = self.jobs[jid]
            if job.state == 'running':
                job.remaining -= 1
                if job.remaining == 0:
                    done.append(job)
        for job in done:
            finish(self, job)
        self.dispatch()

    def cancel(self, root):
        for jid in sorted(descendants(self.jobs, root)):
            job = self.jobs[jid]
            if job.state == 'cancelled':
                continue
            if job.state != 'running':
                self.locks.release(jid)
            job.state, job.remaining = 'cancelled', 0
            job.ticket = job.completed_at = None
            job.dep_versions = {}
            self.history.append(dict(t=self.time, kind='cancel', id=jid, version=job.version))
        self.dispatch()

    def revise(self, event):
        job = self.jobs[event['id']]
        for key in ('duration', 'failures', 'max_retries', 'priority', 'resources'):
            if key in event:
                setattr(job, key, deepcopy(event[key]))
        for jid in sorted(descendants(self.jobs, job.id)):
            self.locks.release(jid)
            self.jobs[jid].reset()
            self.history.append(dict(t=self.time, kind='revise', id=jid,
                                     version=self.jobs[jid].version))
        self.dispatch()
