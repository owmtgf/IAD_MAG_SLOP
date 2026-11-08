def solve(data):
    seen = set()
    duplicates = 0
    documents = {}
    losers = []
    events = []
    for event in data['events']:
        if event['eid'] in seen:
            duplicates += 1
            continue
        seen.add(event['eid'])
        events.append(event)
    events = sorted(events, key=lambda e: (e['version'], e['eid']))
    for event in events:
        doc = event['doc']
        if doc not in documents:
            documents[doc] = {
                'doc': doc,
                'version': 0,
                'deleted': True,
                'fields': {},
                'history': []
            }
        current = documents[doc]
        version = event['version']
        if version <= current['version']:
            losers.append(event['eid'])
            continue
        current['version'] = version
        if event['op'] == 'delete':
            current['deleted'] = True
            effect = 'deleted'
        elif event['op'] == 'put':
            current['fields'].update(event['fields'])
            current['deleted'] = False
            effect = 'put'
        else:
            if current['deleted']:
                current['fields'] = {}
                current['deleted'] = False
            for name in event['unset']:
                current['fields'].pop(name, None)
            current['fields'].update(event['set'])
            effect = 'patched'
        current['history'].append({
            'eid': event['eid'],
            'version': version,
            'effect': effect
        })
    result = []
    for doc in documents:
        current = documents[doc]
        result.append({
            'doc': doc,
            'version': current['version'],
            'deleted': current['deleted'],
            'fields': dict(current['fields']),
            'history': list(current['history'])
        })
    return {
        'documents': result,
        'losers': losers,
        'duplicates': duplicates
    }
