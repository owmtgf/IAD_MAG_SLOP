"""Run the three frozen experiment blocks sequentially, with durable logs.

Usage: python scripts/run_final.py [--resume]
No episode is retried or closed automatically. For interrupted episodes follow
the lab's close-interrupted procedure, then use --resume explicitly.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'runs'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    if not os.environ.get('MAS_LLM_BASE_URL'):
        raise SystemExit('Set MAS_LLM_BASE_URL before starting the experiment.')
    jobs = [
        ('core', 600, ['-m', 'maslab', 'run', '--split', 'test', '--out', 'runs/final']),
        ('extra', 72, ['-m', 'maslab', 'run', '--config', 'docs/extra_config.json',
                       '--freeze', 'extra_freeze.json', '--split', 'extra', '--out', 'runs/extra']),
        ('advanced', 24, ['-m', 'advanced', 'run', '--freeze', 'advanced_freeze.json',
                          '--out', 'runs/advanced']),
    ]
    # Refuse conflicting output before any model calls, including later blocks.
    for folder in ('final', 'extra', 'advanced'):
        destination = RUNS / folder
        if destination.exists() and any(destination.iterdir()) and not args.resume:
            raise SystemExit(f'{destination} already has data; inspect it before --resume.')
    RUNS.mkdir(exist_ok=True)
    state = {'pid': os.getpid(), 'started_unix': time.time(), 'status': 'running',
             'planned_episodes': 696, 'blocks': []}
    state_file = RUNS / 'final_pipeline_status.json'

    def save_state():
        temporary = state_file.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(state_file)

    save_state()
    for name, planned, command in jobs:
        if args.resume:
            command = command + ['--resume']
        block = {'name': name, 'planned': planned, 'started_unix': time.time(),
                 'command': [sys.executable, '-u', *command], 'status': 'running'}
        state['blocks'].append(block)
        save_state()
        print(f'START {name}: {planned} episodes', flush=True)
        log_name = f'final_{name}' + ('_resume' if args.resume else '') + '.log'
        # Append so an explicit continuation cannot overwrite earlier evidence.
        with (RUNS / log_name).open('a', encoding='utf-8') as log:
            result = subprocess.run(block['command'], cwd=ROOT, stdout=log,
                                    stderr=subprocess.STDOUT)
        block.update(returncode=result.returncode, ended_unix=time.time(),
                     status='complete' if result.returncode == 0 else 'failed')
        if result.returncode:
            state.update(status='stopped', ended_unix=time.time())
            save_state()
            print(f'STOP {name}: exit {result.returncode}; inspect {log_name}', flush=True)
            return result.returncode
        save_state()
        print(f'END {name}', flush=True)
    state.update(status='complete', ended_unix=time.time())
    save_state()
    print('All three blocks completed. Validate 696 result files before reporting.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
