def solve(data):
    state = dict(data['base'])
    events = data['events']
    events.sort(key=lambda e: e['seq'])
    for event in events:
        if event['op'] == 'set':
            state[event['key']] = event['value']
        else:
            state.pop(event['key'], None)
    return state