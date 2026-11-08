def solve(data):
    affected = set(data['changed'])
    growing = True
    while growing:
        growing = False
        for node, parents in data['deps'].items():
            if node not in affected and any(p in affected for p in parents):
                affected.add(node)
                growing = True
    
    # Find all nodes that are affected or have affected ancestors
    # We need to find children of affected nodes
    all_affected = set(affected)
    queue = list(affected)
    while queue:
        node = queue.pop(0)
        # Find all nodes that have 'node' as a parent
        for other, parents in data['deps'].items():
            if node in parents and other not in all_affected:
                all_affected.add(other)
                queue.append(other)
    
    # Topological sort for all_affected in lexicographical order
    # A node is ready when all its parents (from data['deps']) are in 'done'
    # Parents not in all_affected are considered already done (unaffected predecessors)
    
    done = set()
    result = []
    
    while len(all_affected) > len(result):
        found = False
        # Sort candidates to ensure deterministic order if multiple are ready
        candidates = sorted([n for n in all_affected if n not in done])
        for node in candidates:
            # Check if all parents are in done
            parents = data['deps'].get(node, [])
            if all(p in done for p in parents):
                result.append(node)
                done.add(node)
                found = True
                break
        if not found:
            # This should not happen in a valid DAG, but break to avoid infinite loop
            break
    
    return result