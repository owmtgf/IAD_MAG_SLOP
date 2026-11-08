def solve(data):
    out = {}
    for department,person,value in data:
        group = out.setdefault(department,{})
        group[person] = group.get(person, 0) + value
    return out