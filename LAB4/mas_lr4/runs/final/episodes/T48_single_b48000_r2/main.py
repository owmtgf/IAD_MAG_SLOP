def solve(data):
    deps = data['deps']
    width = data['width']
    done = set()
    stages = []
    all_tasks = set(deps.keys())
    
    while len(done) < len(all_tasks):
        ready = []
        for k in all_tasks:
            if k in done:
                continue
            parents = deps[k]
            if all(p in done for p in parents):
                ready.append(k)
        
        if not ready:
            return None
        
        ready.sort()
        
        current_stage = []
        for task in ready:
            if len(current_stage) < width:
                current_stage.append(task)
        
        stages.append(current_stage)
        done.update(current_stage)
    
    return stages
