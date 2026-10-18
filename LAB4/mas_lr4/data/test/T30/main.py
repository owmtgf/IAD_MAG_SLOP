def solve(data):
    state = data['base']
    for event in data['events']:
        if event['op'] == 'set':
            state[event['key']] = event['value']
        else:
            state.pop(event['key'],None)
    return state
