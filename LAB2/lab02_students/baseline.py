"""Фиксированный workflow. Два вызова policy без перепланирования после записи."""
import json
from core import parse_action, episode


def run_fixed(policy, env, max_steps=12):
    history = []
    for name in ("read_ticket", "search_policy", "list_resources"):
        if len(history) >= max_steps:
            return episode("budget_exhausted", history, env)
        history.append({"step": len(history)+1, "action": {"type": "tool", "name": name, "args": {}},
                        "observation": env.call(name, {})})
    if not history[-1]["observation"].get("ok"):
        return episode("tool_error", history, env)
    for stage in ("decision", "final"):
        if len(history) >= max_steps:
            return episode("budget_exhausted", history, env)
        try:
            raw = policy.next_action(history)
        except Exception as exc:
            history.append({"step": len(history)+1, "observation": {"ok": False, "error": "model_error",
                             "exception_type": type(exc).__name__}})
            return episode("model_error", history, env)
        event = {"step": len(history)+1, "raw": raw}
        try:
            action = parse_action(raw)
        except ValueError as exc:
            event["observation"] = {"ok": False, "error": str(exc)}
            history.append(event)
            return episode("invalid_output", history, env)
        event["action"] = action
        if action["type"] == "finish":
            event["observation"] = {"ok": True, "final_status": action["status"]}
            history.append(event)
            if action["status"] == "done":
                v = env.snapshot()["validation"]
                if not v or not v["valid"]:
                    return episode("invalid_finish", history, env)
            return episode(action["status"], history, env, action["question"])
        if stage != "decision" or action["name"] != "propose_assignment":
            event["observation"] = {"ok": False, "error": "outside_fixed_workflow"}
            history.append(event)
            return episode("invalid_output", history, env)
        event["observation"] = env.call(action["name"], action["args"])
        history.append(event)
        if not event["observation"]["ok"]:
            return episode("tool_error", history, env)
        if len(history) >= max_steps:
            return episode("budget_exhausted", history, env)
        history.append({"step": len(history)+1,
                        "action": {"type": "tool", "name": "validate_assignment", "args": {}},
                        "observation": env.call("validate_assignment", {})})
    return episode("invalid_output", history, env)
