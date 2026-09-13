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
    raise NotImplementedError("Реализуйте greedy в starter.py")


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
    raise NotImplementedError("Реализуйте contract_net в starter.py")
