def solve(data):
    deps = data['deps']
    width = data['width']
    done = set()
    stages = []
    
    while len(done) < len(deps):
        ready = []
        for k in sorted(deps.keys()):
            if k not in done:
                parents = deps[k]
                if all(p in done for p in parents):
                    ready.append(k)
        
        if not ready:
            return None
        
        ready.sort()
        
        stage = ready[:width]
        stages.append(stage)
        done.update(stage)
    
    return stages
