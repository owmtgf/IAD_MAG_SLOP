def solve(data):
    state = data['base']
    sorted_events = sorted(data['events'], key=lambda x: x['seq'])
    for event in sorted_events:
        if event['op'] == 'set':
            state[event['key']] = event['value']
        else:
            state.pop(event['key'], None)
    return state