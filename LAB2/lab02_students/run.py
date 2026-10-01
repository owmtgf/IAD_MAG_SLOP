import argparse
import csv
import importlib
import json
from pathlib import Path
import statistics
import time
from core import Environment, ScriptedPolicy
from baseline import run_fixed

def percentile(values, p):
    ordered = sorted(values)
    if not ordered:
        return None
    i = (len(ordered)-1)*p
    lo = int(i)
    return ordered[lo] + (ordered[min(lo+1, len(ordered)-1)]-ordered[lo])*(i-lo)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--impl", default="student")
    parser.add_argument("--policy", choices=["scripted", "llm"], default="scripted")
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--mode", choices=["fixed", "agent", "all"], default="all")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--out", default="results")
    args = parser.parse_args()
    if args.repeats < 1 or args.max_steps < 0:
        parser.error("repeats>=1 and max_steps>=0 required")
    implementation = importlib.import_module(args.impl)
    cases = json.loads((Path(__file__).parent / "data" / (args.split+".json")).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    modes = ["fixed", "agent"] if args.mode == "all" else [args.mode]
    rows = []
    for mode in modes:
        for case in cases:
            for repeat in range(args.repeats):
                env = Environment(case)
                if args.policy == "scripted":
                    policy = ScriptedPolicy()
                else:
                    from llm_policy import LLMPolicy
                    policy = LLMPolicy(mode)
                start = time.perf_counter()
                run = run_fixed if mode == "fixed" else implementation.run_agent
                result = run(policy, env, args.max_steps)
                elapsed_ms = (time.perf_counter()-start)*1000
                success = implementation.evaluate(result)
                row = {"case_id": case["id"], "category": case["category"], "mode": mode,
                       "policy": args.policy, "repeat": repeat, "success": int(success),
                       "status": result["status"], "steps": result["steps"],
                       "tool_calls": len(env.calls),
                       "blocked_actions": sum(e.get("observation", {}).get("error") == "assignment_blocked" for e in result["history"]),
                       "errors": sum(e.get("observation", {}).get("ok") is False for e in result["history"]),
                       "elapsed_ms": round(elapsed_ms, 3), **policy.usage}
                result.update({"metrics": row, "model": getattr(policy, "model", None),
                               "temperature": getattr(policy, "temperature", None),
                               "requests": getattr(policy, "requests", []), "max_steps": args.max_steps})
                stem = f'{mode}_{case["id"]}_{repeat}'
                (out/(stem+".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                (out/(stem+".jsonl")).write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in result["history"])+"\n", encoding="utf-8")
                rows.append(row)
    with (out/"results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    summaries = []
    for mode in modes:
        group = [r for r in rows if r["mode"] == mode]
        summary = {"mode": mode, "policy": args.policy, "episodes": len(group),
                   "success_rate": sum(r["success"] for r in group)/len(group),
                   "mean_steps": statistics.mean(r["steps"] for r in group),
                   "p50_ms": round(percentile([r["elapsed_ms"] for r in group], .5), 3),
                   "p95_ms": round(percentile([r["elapsed_ms"] for r in group], .95), 3)}
        summaries.append(summary)
    with (out/"summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0]))
        writer.writeheader(); writer.writerows(summaries)
    (out/"run_config.json").write_text(json.dumps(vars(args), ensure_ascii=False, indent=2))
    print(json.dumps(summaries, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
