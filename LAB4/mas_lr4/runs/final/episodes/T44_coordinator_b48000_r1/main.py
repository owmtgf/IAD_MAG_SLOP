def solve(data):
    best = {}
    def visit(node):
        if node in best:
            return best[node]
        choices = [(data['durations'][node],[node])]
        for parent in data['deps'][node]:
            cost,path = visit(parent)
            choices.append((cost+data['durations'][node],path+[node]))
        best[node] = max(choices,key=lambda x:(x[0],x[1]))
        return best[node]
    all_nodes = set(data['durations'].keys())
    if not all_nodes:
        return {'duration':0,'path':[]}
    choices = [visit(node) for node in all_nodes]
    cost,path = max(choices,key=lambda x:(x[0],x[1]))
    return {'duration':cost,'path':path}
