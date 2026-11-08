def solve(data):
    events = data['events']
    events.sort(key=lambda e: e['seq'])
    state = data['base']
    for event in events:
        if event['op'] == 'set':
            state[event['key']] = event['value']
        else:
            state.pop(event['key'], None)
    return state