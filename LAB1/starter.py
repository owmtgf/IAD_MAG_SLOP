"""Реализуйте два TODO. В этой работе не нужны LLM, сеть и сторонние пакеты."""
from __future__ import annotations
from core import Matrix, Outcome, Contractor, validate_costs, validate_order


def independent(costs: Matrix) -> Outcome:
    """Готово: каждый агент выбирает самую дешёвую задачу своей строки.

    Ничья: меньший индекс задачи. Коллизии НЕ исправляем.
    """
    validate_costs(costs)
    return Outcome([min(range(len(costs)), key=lambda j: (row[j], j))
                    for row in costs])


def greedy(costs: Matrix) -> Outcome:
    """TODO 1: централизованное жадное назначение.

    1. Соберите все тройки (стоимость, индекс агента, индекс задачи).
    2. Отсортируйте их лексикографически.
    3. Возьмите пару, только если и агент, и задача ещё свободны.
    4. Верните Outcome(assignment, communication_modelled=False).

    Не путайте этот алгоритм с последовательным аукционом по задачам.
    """
    validate_costs(costs)
    n = len(costs)
    pairs = sorted(
        (costs[agent_id][task_id], agent_id, task_id)
        for agent_id in range(n)
        for task_id in range(n)
    )

    assignment = [-1] * n
    free_agents = set(range(n))
    free_tasks = set(range(n))
    for _, agent_id, task_id in pairs:
        if agent_id in free_agents and task_id in free_tasks:
            assignment[agent_id] = task_id
            free_agents.remove(agent_id)
            free_tasks.remove(task_id)

    return Outcome(assignment, communication_modelled=False)


def contract_net(agents: list[Contractor], task_order: list[int]) -> Outcome:
    """TODO 2: учебный последовательный Contract Net.

    Менеджер знает список свободных исполнителей, но не их строки стоимости.
    Используйте только agent.agent_id, agent.propose(task), agent.accept(task).
    Все агенты при входе свободны; порядок задач — перестановка 0..n-1.

    Для каждой задачи и m свободных исполнителей:
      CFP каждому (m сообщений), затем PROPOSE от каждого (m);
      ACCEPT победителю и REJECT всем остальным (в сумме m);
      INFORM от победителя менеджеру (1).
    Победитель: минимум (цена заявки, agent_id). Повторных назначений нет.
    Внутри каждой фазы обрабатывайте исполнителей по возрастанию agent_id.

    Формат сообщения:
      {"type": "CFP", "sender": "manager", "receiver": "A0", "task": 0}
    Для PROPOSE добавьте "bid": <положительное целое>.
    Допустимые type: CFP, PROPOSE, ACCEPT, REJECT, INFORM.
    INFORM здесь означает условное завершение, не реальное выполнение работы.

    Верните Outcome(assignment, messages). Один адресат = одно сообщение.
    Это упрощённый протокол без потерь, дедлайнов и параллельных менеджеров,
    а не полная реализация стандарта FIPA или исходного CNET.
    """
    validate_order(task_order, len(agents))
    agents_by_id = {agent.agent_id: agent for agent in agents}
    free_agent_ids = sorted(agents_by_id)
    assignment = [-1] * len(agents)
    messages = []

    for task_id in task_order:
        bids = []
        for agent_id in free_agent_ids:
            messages.append({
                "type": "CFP", "sender": "manager",
                "receiver": f"A{agent_id}", "task": task_id,
            })

        for agent_id in free_agent_ids:
            bid = agents_by_id[agent_id].propose(task_id)
            if bid is None:
                raise ValueError("Свободный исполнитель не должен быть занят.")
            bids.append((bid, agent_id))
            messages.append({
                "type": "PROPOSE", "sender": f"A{agent_id}",
                "receiver": "manager", "task": task_id, "bid": bid,
            })

        _, winner_id = min(bids)
        for agent_id in free_agent_ids:
            message_type = "ACCEPT" if agent_id == winner_id else "REJECT"
            messages.append({
                "type": message_type, "sender": "manager",
                "receiver": f"A{agent_id}", "task": task_id,
            })

        agents_by_id[winner_id].accept(task_id)
        assignment[winner_id] = task_id
        messages.append({
            "type": "INFORM", "sender": f"A{winner_id}",
            "receiver": "manager", "task": task_id,
        })
        free_agent_ids.remove(winner_id)

    return Outcome(assignment, messages)
