def ready_order(jobs):
    return sorted((j for j in jobs.values() if j.state == 'ready'),
                  key=lambda j: (j.ticket, -j.priority, j.id))
