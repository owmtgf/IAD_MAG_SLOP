def solve(data):
    state = data['base']
    events = data['events']
    events.sort(key=lambda x: x['seq'])
    for event in events:
        if event['op'] == 'set':
            state[event['key']] = event['value']
        else:
            state.pop(event['key'], None)
    return state