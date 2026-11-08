def solve(data):
    deps = data['deps']
    width = data['width']
    done = set()
    stages = []
    all_nodes = set(deps.keys())
    
    while len(done) < len(all_nodes):
        ready = []
        for node in all_nodes:
            if node in done:
                continue
            parents = deps.get(node, [])
            if all(p in done for p in parents):
                ready.append(node)
        
        if not ready:
            return None
        
        ready.sort()
        stage = ready[:width]
        stages.append(stage)
        done.update(stage)
    
    return stages
