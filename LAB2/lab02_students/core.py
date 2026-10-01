"""ЛР2. Детерминированная учебная среда. Python 3.10+, только stdlib."""
from copy import deepcopy
import json

TOOLS = {
    "read_ticket": {},
    "search_policy": {},
    "list_resources": {},
    "propose_assignment": {"resource_id": str},
    "validate_assignment": {},
}
FINALS = {"done", "needs_input", "no_solution"}


def parse_action(raw):
    """Строгий контракт; произвольный текст или eval здесь недопустимы."""
    try:
        action = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_json") from exc
    if not isinstance(action, dict):
        raise ValueError("action_must_be_object")
    if action.get("type") == "tool":
        if set(action) != {"type", "name", "args"}:
            raise ValueError("invalid_fields")
        name, args = action["name"], action["args"]
        if not isinstance(name, str) or name not in TOOLS:
            raise ValueError("unknown_tool")
        if not isinstance(args, dict) or set(args) != set(TOOLS[name]):
            raise ValueError("invalid_arguments")
        if any(type(args[k]) is not typ for k, typ in TOOLS[name].items()):
            raise ValueError("invalid_argument_type")
    elif action.get("type") == "finish":
        if set(action) != {"type", "status", "question"}:
            raise ValueError("invalid_fields")
        if not isinstance(action["status"], str) or action["status"] not in FINALS or not isinstance(action["question"], str):
            raise ValueError("invalid_finish")
        if action["status"] == "needs_input" and not action["question"].strip():
            raise ValueError("empty_question")
    else:
        raise ValueError("unknown_action_type")
    return action


class Environment:
    """Модели передаются только результаты call(), но не self.case."""

    def __init__(self, case):
        self.case = deepcopy(case)
        self.ticket = deepcopy(case["ticket"])
        self.resources = deepcopy(case["resources"])
        self.proposal = None
        self.validation = None
        self.transient_used = False
        self.stale_used = False
        self.version = 0
        self.calls = []

    def eligible(self, resource):
        return (self.ticket["skill"] is not None
                and self.ticket["skill"] in resource["skills"]
                and resource["cost"] <= self.ticket["budget"]
                and resource["available"])

    def call(self, name, args):
        # Повторная проверка на границе исполнения.
        parse_action(json.dumps({"type": "tool", "name": name, "args": args}))
        self.calls.append(name)
        if name == "read_ticket":
            return {"ok": True, "ticket": deepcopy(self.ticket)}
        if name == "search_policy":
            return {"ok": True, "policy": {
                "id": "P1", "rules": [
                    "Нужный навык должен быть известен и входить в skills ресурса.",
                    "Ресурс должен быть доступен. cost <= budget.",
                    "Любой допустимый ресурс подходит; оптимальность не требуется.",
                    "При skill=null нужно спросить, какой навык нужен.",
                    "Если навык известен, но допустимых ресурсов нет: no_solution.",
                    "После предложения требуется validate_assignment."]}}
        if name == "list_resources":
            if self.case["fault"] == "transient" and not self.transient_used:
                self.transient_used = True
                return {"ok": False, "error": "temporary_unavailable", "retryable": True}
            return {"ok": True, "resources": deepcopy(self.resources), "version": self.version}
        if name == "propose_assignment":
            if self.case["fault"] == "stale" and not self.stale_used:
                self.stale_used = True
                self.resources[0]["available"] = False
                self.version += 1
            resource = next((r for r in self.resources if r["id"] == args["resource_id"]), None)
            if resource is None or not self.eligible(resource):
                return {"ok": False, "error": "assignment_blocked", "retryable": False,
                        "hint": "Проверьте навык, бюджет и актуальную доступность."}
            self.proposal = {"resource_id": resource["id"], "cost": resource["cost"],
                             "ticket_id": self.ticket["id"], "policy_id": "P1"}
            self.validation = None  # Любая новая запись отменяет прежнюю проверку.
            return {"ok": True, "proposal": deepcopy(self.proposal)}
        if name == "validate_assignment":
            resource = next((r for r in self.resources
                             if self.proposal and r["id"] == self.proposal["resource_id"]), None)
            valid = bool(resource and self.eligible(resource)
                         and self.proposal["cost"] == resource["cost"]
                         and self.proposal["ticket_id"] == self.ticket["id"])
            self.validation = {"valid": valid, "version": self.version,
                               "proposal": deepcopy(self.proposal)}
            return {"ok": True, **deepcopy(self.validation)}
        raise AssertionError("unreachable")

    def snapshot(self):
        """Истина для evaluator. Policy эту структуру не получает."""
        return deepcopy({"ticket": self.ticket, "resources": self.resources,
                         "proposal": self.proposal, "validation": self.validation,
                         "version": self.version})


def tool(name, **args):
    return json.dumps({"type": "tool", "name": name, "args": args}, ensure_ascii=False)


def finish(status, question=""):
    return json.dumps({"type": "finish", "status": status, "question": question}, ensure_ascii=False)


def last_ok(history, name):
    for event in reversed(history):
        if event.get("action", {}).get("name") == name and event.get("observation", {}).get("ok"):
            return event["observation"]
    return None


class ScriptedPolicy:
    """Правило для отладки механики. Это НЕ LLM и НЕ результат эксперимента с LLM."""
    def __init__(self):
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "model_calls": 0}

    def next_action(self, history):
        ticket_obs = last_ok(history, "read_ticket")
        if not ticket_obs:
            return tool("read_ticket")
        if not last_ok(history, "search_policy"):
            return tool("search_policy")
        ticket = ticket_obs["ticket"]
        if ticket["skill"] is None:
            return finish("needs_input", "Какой навык нужен для заявки?")
        resources_obs = last_ok(history, "list_resources")
        last = history[-1] if history else {}
        if not resources_obs or last.get("observation", {}).get("error") == "assignment_blocked":
            return tool("list_resources")
        if last.get("action", {}).get("name") == "validate_assignment":
            return finish("done") if last["observation"].get("valid") else tool("list_resources")
        if last.get("action", {}).get("name") == "propose_assignment" and last.get("observation", {}).get("ok"):
            return tool("validate_assignment")
        eligible = [r for r in resources_obs["resources"] if r["available"]
                    and ticket["skill"] in r["skills"] and r["cost"] <= ticket["budget"]]
        if not eligible:
            return finish("no_solution")
        resource = min(eligible, key=lambda r: (r["cost"], r["id"]))
        return tool("propose_assignment", resource_id=resource["id"])


class ReplayPolicy:
    """Список внешних ответов для проверки контроллера, без стохастики."""
    def __init__(self, actions):
        self.actions = iter(actions)
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "model_calls": 0}

    def next_action(self, history):
        return next(self.actions, finish("done"))


def episode(status, history, env, question=""):
    return {"status": status, "question": question, "steps": len(history),
            "history": deepcopy(history), "state": env.snapshot()}
