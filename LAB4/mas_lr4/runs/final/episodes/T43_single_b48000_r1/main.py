def solve(data):
    finished = {}
    all_nodes = set(data['deps'].keys())
    while len(finished) < len(all_nodes):
        ready = []
        for node in all_nodes:
            if node in finished:
                continue
            parents = data['deps'].get(node, [])
            if all(p in finished for p in parents):
                ready.append(node)
        if not ready:
            return None
        for node in ready:
            parents = data['deps'].get(node, [])
            if not parents:
                start = 0
            else:
                start = max(finished[p] for p in parents)
            finished[node] = start + data['durations'][node]
    return finished
