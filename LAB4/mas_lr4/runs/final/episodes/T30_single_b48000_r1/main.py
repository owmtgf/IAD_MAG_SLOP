def solve(data):
    events = sorted(data['events'], key=lambda x: x['seq'])
    state = dict(data['base'])
    for event in events:
        if event['op'] == 'set':
            state[event['key']] = event['value']
        else:
            state.pop(event['key'], None)
    return state