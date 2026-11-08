from .scheduler import Scheduler
from .events import apply
from .render import render


def solve(data):
    runtime = Scheduler(data['jobs'])
    for index, event in enumerate(data.get('events', [])):
        apply(runtime, event, index)
    return render(runtime)
