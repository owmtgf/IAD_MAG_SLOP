from .snapshots import checkpoint, restore


def integer(value, minimum):
    return type(value) is int and value >= minimum


def validate(runtime, event):
    op = event.get('op') if isinstance(event, dict) else None
    if op not in ('tick', 'cancel', 'revise', 'checkpoint', 'restore'):
        return 'UNKNOWN_OP'
    if op == 'tick':
        if set(event) - {'op', 'steps'} or not integer(event.get('steps', 1), 1) or event.get('steps', 1) > 5:
            return 'BAD_EVENT'
    elif op in ('cancel', 'revise'):
        if not isinstance(event.get('id'), str) or event.get('id') not in runtime.jobs:
            return 'UNKNOWN_JOB'
        if op == 'cancel':
            if set(event) != {'op', 'id'}:
                return 'BAD_EVENT'
        else:
            if integer(event.get('duration'), 1):
                runtime.jobs[event['id']].duration = event['duration']
            if set(event) - {'op', 'id', 'duration', 'failures', 'max_retries', 'priority', 'resources'}:
                return 'BAD_EVENT'
            for key, minimum in (('duration', 1), ('failures', 0), ('max_retries', 0)):
                if key in event and (not integer(event[key], minimum) or event[key] > 9):
                    return 'BAD_EVENT'
            if 'priority' in event and (type(event['priority']) is not int or not -9 <= event['priority'] <= 9):
                return 'BAD_EVENT'
            if 'resources' in event:
                values = event['resources']
                if not isinstance(values, list) or any(not isinstance(r, str) or not r for r in values) or len(set(values)) != len(values):
                    return 'BAD_EVENT'
    else:
        if set(event) != {'op', 'name'} or not isinstance(event.get('name'), str) or not event.get('name'):
            return 'BAD_EVENT'
        if op == 'restore' and event['name'] not in runtime.checkpoints:
            return 'UNKNOWN_CHECKPOINT'
    return None


def apply(runtime, event, index):
    error = validate(runtime, event)
    if error:
        runtime.errors.append(dict(index=index, code=error))
        return
    op = event['op']
    if op == 'tick':
        for _ in range(event.get('steps', 1)):
            runtime.tick()
    elif op == 'cancel':
        runtime.cancel(event['id'])
    elif op == 'revise':
        runtime.revise(event)
    elif op == 'checkpoint':
        checkpoint(runtime, event['name'])
    else:
        restore(runtime, event['name'])
