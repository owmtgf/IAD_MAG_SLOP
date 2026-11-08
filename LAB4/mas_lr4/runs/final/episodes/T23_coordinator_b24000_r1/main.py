def solve(data):
    out = {}
    for department,person,value in data:
        group = out.setdefault(department,{})
        group[person] = value
    return out
