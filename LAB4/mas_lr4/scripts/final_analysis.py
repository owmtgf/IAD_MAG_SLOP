"""Validate final artifacts and build submission tables, without model calls."""
import collections
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from maslab.runner import fingerprint
from advanced.__main__ import fingerprint as advanced_fingerprint


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def med(values):
    return statistics.median(values) if values else None


def csv_save(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    out = ROOT / 'analysis' / 'final'
    out.mkdir(parents=True, exist_ok=True)
    freeze_checks = {
        'core': read(ROOT / 'freeze.json') == fingerprint(ROOT / 'config.json', 'maslab.student_policies'),
        'C': read(ROOT / 'extra_freeze.json') == fingerprint(ROOT / 'docs/extra_config.json', 'maslab.student_policies'),
        'M': read(ROOT / 'advanced_freeze.json') == advanced_fingerprint(ROOT / 'advanced/config.json', 'advanced.student_policies'),
    }
    if not all(freeze_checks.values()):
        raise ValueError('Frozen files changed')
    groups = collections.defaultdict(list)
    validation, statuses, roles = [], [], []
    api_errors = collections.Counter()
    all_results = {}
    overhead_details = []
    for folder, count in [('final', 600), ('extra', 72), ('advanced', 24)]:
        root = ROOT / 'runs' / folder
        manifest = read(root / 'manifest.json')
        if len(manifest['jobs']) != count:
            raise ValueError('Unexpected matrix: ' + folder)
        if len(list((root / 'episodes').glob('*/result.json'))) != count:
            raise ValueError('Missing or extra results: ' + folder)
        seen = set()
        for job in manifest['jobs']:
            ident = job['episode_id']
            if ident in seen:
                raise ValueError('Duplicate manifest job')
            seen.add(ident)
            episode = root / 'episodes' / ident
            result = read(episode / 'result.json')
            if any(type(result.get(k)) is not type(v) or result[k] != v for k, v in job.items()):
                raise ValueError('Mismatched episode: ' + ident)
            trace = episode / 'trace.jsonl'
            events = [json.loads(line) for line in trace.read_text().splitlines()]
            if result['status'] != 'interrupted' and not any(e['event'] == 'episode_end' for e in events):
                raise ValueError('Missing episode_end: ' + ident)
            recorded_in = recorded_out = 0
            for event in events:
                if event['event'] == 'model_error':
                    api_errors[(folder, event.get('detail', 'unknown'))] += 1
                if event['event'] == 'model_response':
                    usage = event.get('usage')
                    if type(usage) is dict and all(type(usage.get(k)) is int for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')):
                        if usage['prompt_tokens'] + usage['completion_tokens'] != usage['total_tokens']:
                            raise ValueError('Usage mismatch: ' + ident)
                        recorded_in += usage['prompt_tokens']
                        recorded_out += usage['completion_tokens']
                    if event.get('model') and event['model'] != manifest['config']['model']:
                        raise ValueError('Unexpected model: ' + ident)
            if folder == 'final':
                last_response = next((e for e in reversed(events) if e['event'] == 'model_response'), None)
                try:
                    last_action = json.loads(last_response['content']) if last_response else {}
                except (ValueError, TypeError):
                    last_action = {}
                overhead_details.append({
                    'budget': result['budget'], 'architecture': result['architecture'],
                    'result': result,
                    'reviewer_reached': any(e['event'] == 'model_request' and e.get('role') == 'reviewer' for e in events),
                    'delegation_limit': any(e['event'] == 'model_request' and e.get('role') == 'coordinator' and
                        'role turn limit reached' in e['messages'][-1].get('content', '').lower() for e in events),
                    'finish_over_budget': any(e['event'] == 'budget_overrun' for e in events) and
                        type(last_action) is dict and last_action.get('action') == 'finish',
                })
            if result['status'] != 'interrupted':
                if (recorded_in, recorded_out) != (result['input_tokens_known'], result['output_tokens_known']):
                    raise ValueError('Trace/result usage mismatch: ' + ident)
                if recorded_in + recorded_out != result['total_tokens_known']:
                    raise ValueError('Total usage mismatch: ' + ident)
                if sum(u['total'] for u in result['tokens_by_role'].values()) != result['total_tokens_known']:
                    raise ValueError('Role usage mismatch: ' + ident)
            if result.get('code_sha256'):
                if hashlib.sha256((episode / 'main.py').read_bytes()).hexdigest() != result['code_sha256']:
                    raise ValueError('Artifact hash mismatch: ' + ident)
            if folder == 'advanced':
                if result.get('success') is not None:
                    raise ValueError('M correctness must remain unknown')
                if result['task_id'] != 'M04':
                    task = read(ROOT / 'advanced/tasks' / result['task_id'] / 'task.json')
                    files = {name: (episode / 'project' / name).read_text() for name in sorted(task['editable_files'])}
                    artifact = files
                else:
                    # No M04 program/answer was submitted in this experiment.
                    if (episode / 'answer.json').exists():
                        raise ValueError('Update M04 artifact validation for submitted answers')
                    artifact = {'answer': None, 'program': None}
                digest = hashlib.sha256(json.dumps(artifact, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                if digest != result['artifact_sha256']:
                    raise ValueError('M artifact hash mismatch: ' + ident)
            block = ('M04' if result['task_id'] == 'M04' else 'M01-M03') if folder == 'advanced' else ('T' if folder == 'final' else 'C')
            groups[(block, result['budget'], result['architecture'])].append(result)
            all_results[(folder, ident)] = result
            for role, usage in result.get('tokens_by_role', {}).items():
                roles.append({'block': block, 'episode_id': ident, 'architecture': result['architecture'],
                              'budget': result['budget'], 'role': role, **usage,
                              'episode_usage_complete': result['usage_complete']})
        validation.append({'folder': folder, 'planned': count, 'validated_results': len(seen)})

    summary = []
    for (block, budget, architecture), rows in sorted(groups.items()):
        known = [r for r in rows if r['usage_complete'] is True]
        durations = [r['seconds'] for r in rows if r.get('seconds') is not None]
        reports = [r.get('visible_report', r.get('final_report', {})) for r in rows]
        completed = sum(r.get('success') is True or r.get('finished') is True for r in rows)
        full_examples = [v['open_program_examples'] for v in reports if 'open_program_examples' in v]
        counts = collections.Counter(r['status'] for r in rows)
        summary.append({
            'block': block, 'budget': budget, 'architecture': architecture, 'planned': len(rows),
            'workflow_successes': completed, 'workflow_success_rate': completed / len(rows),
            'open_all_passed': sum(v.get('passed') is True for v in reports),
            'closed_correctness': 'not_checked',
            'median_tokens_complete_usage': med([r['total_tokens_known'] for r in known]),
            'known_token_episodes': len(known), 'unknown_usage': len(rows) - len(known),
            'median_seconds': med(durations), 'known_time_episodes': len(durations),
            'median_model_calls': med([r['model_calls'] for r in rows if 'model_calls' in r]),
            'budget_exhausted': counts['budget_exhausted'],
            'budget_exhausted_rate': counts['budget_exhausted'] / len(rows),
            'schema_valid': sum(v.get('schema_valid') is True for v in reports) if block == 'M04' else None,
            'example_checks_executed': len(full_examples) if block == 'M04' else None,
            'example_all_passed': sum(v['passed_count'] == v['total'] for v in full_examples) if block == 'M04' else None,
        })
        statuses.extend({'block': block, 'budget': budget, 'architecture': architecture,
                         'status': status, 'count': n} for status, n in sorted(counts.items()))
    csv_save(out / 'summary.csv', summary)
    csv_save(out / 'statuses.csv', statuses)
    csv_save(out / 'tokens_by_role.csv', roles)
    overhead = []
    for budget, architecture in sorted({(r['budget'], r['architecture']) for r in overhead_details}):
        rows = [r for r in overhead_details if (r['budget'], r['architecture']) == (budget, architecture)]
        known = [r['result'] for r in rows if r['result']['usage_complete']]
        overhead.append({
            'budget': budget, 'architecture': architecture, 'episodes': len(rows),
            'complete_usage_episodes': len(known),
            'input_token_share_percent': 100 * sum(r['input_tokens_known'] for r in known) /
                sum(r['total_tokens_known'] for r in known),
            'open_passed_but_workflow_failed': sum(r['result'].get('visible_passed') is True and
                not r['result']['success'] for r in rows),
            'fixed_before_reviewer': sum(not r['reviewer_reached'] for r in rows) if architecture == 'fixed' else None,
            'coordinator_delegation_limit_episodes': sum(r['delegation_limit'] for r in rows) if architecture == 'coordinator' else None,
            'finish_response_over_budget': sum(r['finish_over_budget'] for r in rows),
        })
    csv_save(out / 'process_overhead.csv', overhead)

    # Compare actual public-test observations, not only text hashes.
    answer_rows = []
    for folder, label in [('final', 'T'), ('extra', 'C')]:
        manifest = read(ROOT / 'runs' / folder / 'manifest.json')
        keys = sorted({(j['task_id'], j['budget'], j['repeat']) for j in manifest['jobs']})
        for task, budget, repeat in keys:
            base = all_results[(folder, f'{task}_single_b{budget}_r{repeat}')]
            for team in ('fixed', 'coordinator'):
                other = all_results[(folder, f'{task}_{team}_b{budget}_r{repeat}')]
                observations = []
                for r in (base, other):
                    cases = r.get('final_report', {}).get('cases', [])
                    complete = len(cases) == r.get('visible_total') and all('actual' in c for c in cases)
                    observations.append({c['id']: c['actual'] for c in cases} if complete else None)
                answer_rows.append({'block': label, 'task_id': task, 'budget': budget,
                    'repeat': repeat, 'team': team,
                    'comparable': all(v is not None for v in observations),
                    'same_open_observations': observations[0] == observations[1] if all(v is not None for v in observations) else None})
    csv_save(out / 'open_answer_pairs.csv', answer_rows)
    agreement = []
    for block, budget, team in sorted({(r['block'], r['budget'], r['team']) for r in answer_rows}):
        rows = [r for r in answer_rows if (r['block'], r['budget'], r['team']) == (block, budget, team)]
        agreement.append({'block': block, 'budget': budget, 'team': team,
                          'pairs': len(rows), 'comparable': sum(r['comparable'] for r in rows),
                          'same': sum(r['same_open_observations'] is True for r in rows),
                          'different': sum(r['same_open_observations'] is False for r in rows)})
    csv_save(out / 'open_answer_agreement.csv', agreement)
    audit = {'planned_total': 696, 'validated_total': sum(r['validated_results'] for r in validation),
             'runs': validation, 'freeze_matches': freeze_checks,
             'api_errors': [{'run': name, 'reason': reason, 'count': n} for (name, reason), n in sorted(api_errors.items())],
             'note': 'All failures retained. Unknown usage is not zero. M success remains null.'}
    (out / 'validation.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    print('Open-output agreement:', json.dumps(agreement, ensure_ascii=False))


if __name__ == '__main__':
    main()
