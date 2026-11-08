class ResourceLocks:
    def __init__(self):
        self.owners = {}

    def acquire(self, job, reserved):
        needed = set(job.resources)
        unavailable = set(self.owners) | reserved
        if needed & unavailable:
            for resource in sorted(needed - unavailable):
                self.owners[resource] = job.id
            return False
        for resource in needed:
            self.owners[resource] = job.id
        return True

    def release(self, jid):
        for resource in list(self.owners):
            if self.owners[resource] == jid:
                del self.owners[resource]

    def reserve_waiter(self, job, reserved):
        reserved.update(set(job.resources) & set(self.owners))
