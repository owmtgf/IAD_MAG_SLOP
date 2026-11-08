from copy import deepcopy


def checkpoint(runtime, name):
    if name not in runtime.checkpoints:
        runtime.checkpoints[name] = (dict(runtime.jobs), runtime.time, runtime.next_ticket,
                                    dict(runtime.locks.owners), list(runtime.history))


def restore(runtime, name):
    jobs, time, ticket, locks, history = deepcopy(runtime.checkpoints[name])
    runtime.jobs, runtime.time, runtime.next_ticket = jobs, time, ticket
    runtime.locks.owners, runtime.history = locks, history
    runtime.history.append(dict(t=time, kind='restore', name=name))
