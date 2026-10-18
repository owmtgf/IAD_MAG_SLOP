def solve(data):
    capacity,used,release = data
    if release >= used:
        return None
    used -= release
    return {'used':used,'free':capacity-used}
