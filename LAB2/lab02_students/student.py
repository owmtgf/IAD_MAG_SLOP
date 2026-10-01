"""Реализуйте только две функции. Контракты описаны в TASK.md."""
from core import parse_action, episode


def run_agent(policy, env, max_steps=12):
    """TODO: цикл, обработка ответа, dispatch, история и остановка.

    policy.next_action(history) возвращает строку JSON.
    В history: step, raw, action (если разобран), observation.
    ValueError от parse_action: observation={ok:False,error:str(exc)};
    такой ответ расходует шаг, но env.call не вызывается.
    Ошибка policy: статус model_error, попытку также записать.
    finish(done) допустим только после актуальной успешной validation.
    Преждевременный done: observation.error='finish_without_validation', продолжить.
    finish(needs_input/no_solution) завершает цикл; правильность проверит evaluator.
    Последний допустимый finish имеет приоритет над budget_exhausted.
    Выход: core.episode(status, history, env, question).
    Не передавайте env, case или snapshot в policy.
    """
    history = []

    # ``range`` also handles max_steps=0: in that case the episode has no
    # attempted actions and is immediately out of budget.
    for step in range(1, max_steps + 1):
        try:
            raw = policy.next_action(history)
        except Exception as exc:
            history.append({
                "step": step,
                "observation": {
                    "ok": False,
                    "error": "model_error",
                    "exception_type": type(exc).__name__,
                },
            })
            return episode("model_error", history, env)

        event = {"step": step, "raw": raw}
        try:
            action = parse_action(raw)
        except ValueError as exc:
            # Invalid output is an observation for the policy, not a tool call.
            event["observation"] = {"ok": False, "error": str(exc)}
            history.append(event)
            continue

        event["action"] = action
        if action["type"] == "tool":
            # The environment performs a second, authoritative validation at
            # its execution boundary.
            event["observation"] = env.call(action["name"], action["args"])
            history.append(event)
            continue

        # The evaluator checks whether needs_input/no_solution is true. The
        # controller itself only has to enforce the stronger done precondition.
        if action["status"] == "done":
            state = env.snapshot()
            proposal = state["proposal"]
            validation = state["validation"]
            valid_done = (
                proposal is not None
                and validation is not None
                and validation.get("valid") is True
                and validation.get("version") == state["version"]
                and validation.get("proposal") == proposal
            )
            if not valid_done:
                event["observation"] = {
                    "ok": False,
                    "error": "finish_without_validation",
                }
                history.append(event)
                continue

        event["observation"] = {"ok": True, "final_status": action["status"]}
        history.append(event)
        return episode(action["status"], history, env, action["question"])

    return episode("budget_exhausted", history, env)


def evaluate(result):
    """TODO: вернуть bool успеха по result['state'], статусу и вопросу.

    done: реальное допустимое предложение + актуальная положительная validation.
    needs_input: skill отсутствует, предложения нет, вопрос явно о навыке.
    no_solution: skill известен, допустимых ресурсов нет, предложения нет.
    Остальные статусы неуспешны. Не доверяйте одному флагу validation.valid.
    """
    state = result.get("state", {})
    ticket = state.get("ticket")
    resources = state.get("resources")
    proposal = state.get("proposal")
    validation = state.get("validation")
    if not isinstance(ticket, dict) or not isinstance(resources, list):
        return False

    skill = ticket.get("skill")
    status = result.get("status")

    if status == "needs_input":
        question = result.get("question", "")
        return (
            skill is None
            and proposal is None
            and isinstance(question, str)
            and bool(question.strip())
            and ("навык" in question.lower() or "skill" in question.lower())
        )

    def eligible(resource):
        return (
            isinstance(resource, dict)
            and skill is not None
            and skill in resource.get("skills", [])
            and resource.get("available") is True
            and isinstance(resource.get("cost"), (int, float))
            and resource["cost"] <= ticket.get("budget")
        )

    if status == "no_solution":
        return skill is not None and proposal is None and not any(eligible(r) for r in resources)

    if status != "done" or not isinstance(proposal, dict) or not isinstance(validation, dict):
        return False

    resource = next((r for r in resources if isinstance(r, dict)
                     and r.get("id") == proposal.get("resource_id")), None)
    return (
        resource is not None
        and eligible(resource)
        and proposal.get("ticket_id") == ticket.get("id")
        and proposal.get("policy_id") == "P1"
        and proposal.get("cost") == resource.get("cost")
        and validation.get("valid") is True
        and validation.get("version") == state.get("version")
        and validation.get("proposal") == proposal
    )
