def solve(data):
    done = set()
    stages = []
    while len(done) < len(data['deps']):
        ready = sorted(k for k,parents in data['deps'].items() if k not in done and all(p in done for p in parents))
        if not ready:
            return None
        stage = ready
        stages.append(stage)
        done.update(ready)
    return stages
