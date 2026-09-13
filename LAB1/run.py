"""CLI: валидирует назначения, запускает сравнение и сохраняет CSV + JSON."""
from __future__ import annotations
import argparse
import csv
import importlib.util
import json
from pathlib import Path
from time import perf_counter
import sys
import core

BASE = Path(__file__).resolve().parent


def load_impl(path: Path):
    spec = importlib.util.spec_from_file_location('student_implementation', path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Не удалось загрузить модуль {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--impl', type=Path, default=BASE / 'starter.py')
    p.add_argument('--data', type=Path, default=BASE / 'data' / 'cases.json')
    p.add_argument('--case', help='Например, demo_17_vs_5. Без флага: все 30 матриц.')
    p.add_argument('--methods', nargs='+', choices=['independent','greedy','contract_net','exact'],
                   default=['independent','greedy','contract_net','exact'])
    p.add_argument('--order', help='Порядок задач через запятую; только с --case.')
    p.add_argument('--out', type=Path, default=BASE / 'results')
    args = p.parse_args()
    if args.order and not args.case:
        p.error('--order допустим только вместе с --case')
    try:
        impl = load_impl(args.impl)
        data = json.loads(args.data.read_text(encoding='utf-8'))
        cases = [c for c in data['cases'] if not args.case or c['id'] == args.case]
        if not cases:
            raise ValueError(f"Матрица {args.case!r} не найдена.")
        rows, traces = [], {}
        for case in cases:
            costs = case['costs']
            core.validate_costs(costs)
            n = len(costs)
            order = [int(x) for x in args.order.split(',')] if args.order else list(range(n))
            core.validate_order(order, n)
            optimal = core.exact(costs)
            opt_cost = sum(costs[i][t] for i,t in enumerate(optimal.assignment))
            for method in args.methods:
                started = perf_counter()
                if method == 'exact':
                    result = core.exact(costs)
                elif method == 'contract_net':
                    result = impl.contract_net(core.make_contractors(costs), order)
                else:
                    result = getattr(impl, method)(costs)
                elapsed = (perf_counter() - started) * 1000
                metrics = core.evaluate(costs, result, opt_cost)
                rows.append(dict(case_id=case['id'], family=case['family'], n=n,
                                 method=method, **metrics, elapsed_ms=round(elapsed, 6),
                                 task_order=order if method=='contract_net' else None))
                traces[f"{case['id']}:{method}"] = result.messages
        args.out.mkdir(parents=True, exist_ok=True)
        with (args.out/'results.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        summaries = []
        for method in args.methods:
            mr = [r for r in rows if r['method'] == method]
            valid = [r for r in mr if r['feasible']]
            gaps = [float(r['gap_pct']) for r in valid]
            comm = [int(r['messages']) for r in mr if r['messages'] is not None]
            summaries.append(dict(
                method=method, cases=len(mr), feasible=len(valid),
                feasible_pct=round(100*len(valid)/len(mr), 3),
                mean_cost_valid=round(sum(int(r['cost']) for r in valid)/len(valid), 3) if valid else None,
                mean_gap_pct_valid=round(sum(gaps)/len(gaps), 3) if gaps else None,
                max_gap_pct_valid=round(max(gaps), 3) if gaps else None,
                optimal_cases=sum(r['feasible'] and r['cost']==r['optimal_cost'] for r in mr),
                mean_messages=round(sum(comm)/len(comm), 3) if comm else None))
        with (args.out/'summary.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(summaries[0]))
            writer.writeheader(); writer.writerows(summaries)
        (args.out/'traces.json').write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding='utf-8')
        (args.out/'results.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"{'method':<15} {'valid':>8} {'mean gap%':>11} {'optimal':>9} {'messages':>10}")
        for r in summaries:
            gap='n/a' if r['mean_gap_pct_valid'] is None else f"{r['mean_gap_pct_valid']:.3f}"
            msg='n/a' if r['mean_messages'] is None else str(r['mean_messages'])
            print(f"{r['method']:<15} {r['feasible']:>3}/{r['cases']:<4} {gap:>11} {r['optimal_cases']:>9} {msg:>10}")
        print(f"\nСохранено: {args.out.resolve()}")
        print('gap считается ТОЛЬКО для валидных назначений. Пустое messages = не моделировалось.')
        return 0
    except NotImplementedError as e:
        print(f"TODO: {e}\nДля первого запуска используйте --methods independent exact", file=sys.stderr)
        return 2
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
