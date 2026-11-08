def solve(data):
    done = set()
    stages = []
    total_tasks = len(data['deps'])
    
    while len(done) < total_tasks:
        ready = sorted(k for k, parents in data['deps'].items() if k not in done and all(p in done for p in parents))
        
        if not ready:
            return None
        
        # Разбиваем отсортированный список на подэтапы по размеру width
        width = data['width']
        current_stage = []
        for task in ready:
            current_stage.append(task)
            if len(current_stage) >= width:
                stages.append(current_stage)
                current_stage = []
        
        if current_stage:
            stages.append(current_stage)
        
        done.update(ready)
    
    return stages
