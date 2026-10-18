"""Provided baseline. It may inspect, patch, test and revise repeatedly."""
def single(engine):
    feedback = 'Исправь программу по контракту и проверь результат.'
    while True:
        result = engine.run_role('single',feedback,max_turns=6)
        if result['finish_requested']:
            if engine.finish():
                return
            feedback = 'Текущая программа не прошла реальные проверки. Продолжи исправление.'
        else:
            feedback = 'Продолжи работу. Для завершения используй finish после проверки.'
