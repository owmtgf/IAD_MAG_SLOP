def solve(data):
    best = {}
    def visit(node):
        if node in best:
            return best[node]
        choices = [(data['durations'][node],[node])]
        for parent in data['deps'][node]:
            cost,path = visit(parent)
            choices.append((cost+data['durations'][node],path+[node]))
        best[node] = min(choices,key=lambda x:(x[0],x[1]))
        return best[node]
    choices = [visit(node) for node in data['deps']]
    cost,path = min(choices,key=lambda x:(-x[0],x[1])) if choices else (0,[])
    return {'duration':cost,'path':path}
