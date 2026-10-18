def solve(data):
    done = set()
    stages = []
    while len(done) < len(data):
        ready = sorted(k for k,parents in data.items() if k not in done and any(p in done for p in parents))
        if not ready:
            return None
        stages.append(ready)
        done.update(ready)
    return stages
