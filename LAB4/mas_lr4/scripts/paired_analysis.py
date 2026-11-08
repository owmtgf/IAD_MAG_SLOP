"""Paired descriptive analysis of completed core/C runs; never calls an LLM."""
import argparse
import collections
import csv
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]


def median(values):
    return statistics.median(values) if values else None


def load_run(folder):
    manifest = json.loads((folder / 'manifest.json').read_text())
    results = {}
    for job in manifest['jobs']:
        path = folder / 'episodes' / job['episode_id'] / 'result.json'
        result = json.loads(path.read_text())
        for key, value in job.items():
            if type(result.get(key)) is not type(value) or result[key] != value:
                raise ValueError(f'Mismatched identity: {path}, {key}')
        if type(result.get('success')) is not bool:
            raise ValueError(f'No binary success metric: {path}')
        if result['success'] != (result['status'] == 'success'):
            raise ValueError(f'Inconsistent success/status: {path}')
        if result.get('usage_complete') is True:
            counts = [result.get(k) for k in (
                'input_tokens_known', 'output_tokens_known', 'total_tokens_known')]
            if any(type(x) is not int or x < 0 for x in counts) or sum(counts[:2]) != counts[2]:
                raise ValueError(f'Invalid complete usage: {path}')
        key = (job['task_id'], job['budget'], job['repeat'], job['architecture'])
        if key in results:
            raise ValueError(f'Duplicate episode: {key}')
        results[key] = result
    return results


def pairs(results, themes, block):
    keys = sorted({(task, budget, repeat) for task, budget, repeat, _ in results})
    rows = []
    for task, budget, repeat in keys:
        baseline = results[(task, budget, repeat, 'single')]
        for architecture in ('fixed', 'coordinator'):
            team = results[(task, budget, repeat, architecture)]
            if baseline['seed'] != team['seed']:
                raise ValueError(f'Unmatched seeds: {task}, {budget}, {repeat}')
            a, b = baseline['success'], team['success']
            outcome = ('both_success' if a and b else 'single_only' if a else
                       'team_only' if b else 'both_failure')
            tokens_known = (baseline.get('usage_complete') is True and
                            team.get('usage_complete') is True)
            time_known = all(type(r.get('seconds')) in (int, float) for r in (baseline, team))
            row = {
                'block': block, 'task_id': task, 'theme': themes.get(task, 'unknown'),
                'budget': budget, 'repeat': repeat, 'seed': baseline['seed'],
                'team': architecture, 'outcome': outcome,
                'single_episode_id': baseline['episode_id'],
                'team_episode_id': team['episode_id'],
                'single_status': baseline['status'], 'team_status': team['status'],
                'single_success': a, 'team_success': b,
                'single_visible_passed': baseline.get('visible_passed'),
                'team_visible_passed': team.get('visible_passed'),
                'tokens_pair_complete': tokens_known,
                'single_tokens': baseline.get('total_tokens_known') if baseline.get('usage_complete') else None,
                'team_tokens': team.get('total_tokens_known') if team.get('usage_complete') else None,
                'token_delta_team_minus_single': (
                    team['total_tokens_known'] - baseline['total_tokens_known'] if tokens_known else None),
                'single_seconds': baseline.get('seconds'), 'team_seconds': team.get('seconds'),
                'seconds_delta_team_minus_single': (
                    team['seconds'] - baseline['seconds'] if time_known else None),
                'single_calls': baseline.get('model_calls'), 'team_calls': team.get('model_calls'),
                'same_code_hash': (
                    baseline['code_sha256'] == team['code_sha256']
                    if baseline.get('code_sha256') and team.get('code_sha256') else None),
            }
            rows.append(row)
    return rows


def summarize(rows, keys):
    groups = collections.defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    output = []
    for key, group in sorted(groups.items()):
        counts = collections.Counter(row['outcome'] for row in group)
        wins, losses = counts['team_only'], counts['single_only']
        baseline_successes = sum(row['single_success'] for row in group)
        team_successes = sum(row['team_success'] for row in group)
        assert sum(counts.values()) == len(group)
        assert wins - losses == team_successes - baseline_successes
        known = [row for row in group if row['tokens_pair_complete']]
        times = [row for row in group if row['seconds_delta_team_minus_single'] is not None]
        both_known = [row for row in known if row['outcome'] == 'both_success']
        output.append({
            **dict(zip(keys, key)), 'pairs': len(group),
            'both_success': counts['both_success'], 'both_failure': counts['both_failure'],
            'team_only': wins, 'single_only': losses,
            'single_successes': baseline_successes, 'team_successes': team_successes,
            'net_team_wins': wins - losses,
            'success_delta_percentage_points': 100 * (wins - losses) / len(group),
            'complete_token_pairs': len(known),
            'median_paired_token_delta': median([r['token_delta_team_minus_single'] for r in known]),
            'median_paired_token_ratio': median([
                r['team_tokens'] / r['single_tokens'] for r in known if r['single_tokens'] > 0]),
            'complete_time_pairs': len(times),
            'median_paired_seconds_delta': median([r['seconds_delta_team_minus_single'] for r in times]),
            'both_success_complete_token_pairs': len(both_known),
            'both_success_median_paired_token_delta': median([
                r['token_delta_team_minus_single'] for r in both_known]),
            'identical_code_pairs': sum(r['same_code_hash'] is True for r in group),
        })
    return output


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'analysis' / 'paired')
    args = parser.parse_args()
    with (ROOT / 'data/catalog.csv').open(encoding='utf-8-sig', newline='') as stream:
        themes = {row['id']: row['theme'] for row in csv.DictReader(stream)}
    all_pairs = []
    for block, name, expected in [('core', 'final', 600), ('C', 'extra', 72)]:
        results = load_run(ROOT / 'runs' / name)
        if len(results) != expected:
            raise ValueError(f'Incomplete {block}: {len(results)}/{expected}')
        all_pairs.extend(pairs(results, themes, block))
    summaries = summarize(all_pairs, ['block', 'budget', 'team'])
    by_theme = summarize(all_pairs, ['block', 'budget', 'team', 'theme'])
    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / 'pairs.csv', all_pairs)
    write_csv(args.out / 'summary.csv', summaries)
    write_csv(args.out / 'by_theme.csv', by_theme)
    (args.out / 'summary.json').write_text(json.dumps({
        'pair_key': ['task_id', 'budget', 'repeat'],
        'reference': 'single', 'summaries': summaries,
        'limitations': [
            'Descriptive comparison; two repeats of one task are not independent tasks.',
            'All failures, including API errors and the interrupted episode, remain in success counts.',
            'Token deltas use only pairs with complete usage on both sides; time deltas require both durations.',
            'Median of paired deltas is not the difference between separate medians.',
            'Both-success resource comparison is a selected subset, not whole-sample cost.',
            'Identical code hashes mean identical text, not semantic equivalence of different programs.',
            'C uses open-test workflow success; no closed correctness is inferred.',
            'M excluded: success=null, teacher verification required.',
        ],
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = [
        '# Парное сравнение с single', '',
        'Пара: одна задача, бюджет и повтор; seed проверен на совпадение. '
        'Ошибки API, прерывание и исчерпание бюджета считаются неуспехами.', '',
        '| Блок | Бюджет | Команда | Оба успешны | Только команда | Только single | Оба неуспешны | Разница, п.п. |',
        '|---|---:|---|---:|---:|---:|---:|---:|',
    ]
    for row in summaries:
        lines.append('| {block} | {budget} | {team} | {both_success} | {team_only} | '
                     '{single_only} | {both_failure} | {success_delta_percentage_points:+.1f} |'.format(**row))
    lines += ['',
        'Победа команды — team_only; поражение — single_only. Разница долей '
        'равна (победы − поражения) / число пар. Для core по 100 пар в строке, '
        'для C по 24; строки нельзя суммировать как независимые наблюдения.', '',
        'В summary.csv указаны медианы разностей токенов и времени в тех же '
        'парах (команда минус single), число доступных пар и отдельная оценка '
        'расхода среди пар с двумя успехами. Неизвестный usage не заменён нулём. '
        'Время прерванного эпизода неизвестно и исключено только из временной '
        'метрики, не из сравнения успехов.', '',
        'Полные 448 пар — pairs.csv; разбор по темам — by_theme.csv. '
        'Совпадение хешей кода означает одинаковый текст. Разные хеши не '
        'доказывают разные результаты программы.', '',
        'Это описательные результаты: два повтора одной задачи не являются '
        'двумя независимыми задачами. Статистическая значимость не заявляется. '
        'Для C показан успех по открытым проверкам; M не включён, поскольку '
        'его итоговая правильность требует проверки преподавателя.', '',
        'Воспроизведение из корня mas_lr4: `python scripts/paired_analysis.py`.', '',
    ]
    (args.out / 'README.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
