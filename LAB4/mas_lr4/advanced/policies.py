"""Unchanged baseline shared by all new-task comparisons."""
def single(engine):
    while not engine.finished:
        engine.run_role('single', 'Реши задачу, проверь и заверши роль.', engine.config['max_model_calls'])
        if engine.finish():
            return
