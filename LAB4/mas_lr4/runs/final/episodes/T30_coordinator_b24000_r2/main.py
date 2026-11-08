def solve(data):
    base = dict(data['base'])
    events = sorted(data['events'], key=lambda x: x['seq'])
    for event in events:
        if event['op'] == 'set':
            base[event['key']] = event['value']
        else:
            base.pop(event['key'], None)
    return base