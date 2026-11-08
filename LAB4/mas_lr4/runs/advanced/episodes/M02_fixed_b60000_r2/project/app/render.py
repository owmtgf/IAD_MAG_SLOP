from copy import deepcopy
from .ordering import ready_order


def render(runtime):
    fields = ('id', 'version', 'state', 'attempts', 'remaining', 'ticket', 'completed_at', 'dep_versions')
    return dict(time=runtime.time, next_ticket=runtime.next_ticket,
                jobs=[{key: deepcopy(getattr(runtime.jobs[jid], key)) for key in fields}
                      for jid in sorted(runtime.jobs)],
                queue=[job.id for job in ready_order(runtime.jobs)],
                locks=dict(sorted(runtime.locks.owners.items())),
                checkpoints=sorted(runtime.checkpoints), history=deepcopy(runtime.history),
                errors=deepcopy(runtime.errors))
