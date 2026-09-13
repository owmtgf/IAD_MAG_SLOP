"""Общие типы, проверка результата и точный baseline. Python 3.10+, без pip."""
from __future__ import annotations
from dataclasses import dataclass, field
from itertools import permutations
from typing import Optional

Matrix = list[list[int]]
Message = dict[str, object]


def validate_costs(costs: Matrix) -> None:
    """Матрица должна быть непустой, квадратной, из положительных целых."""
    if not isinstance(costs, list) or not costs:
        raise ValueError("Ожидается непустая квадратная матрица.")
    n = len(costs)
    if any(not isinstance(row, list) or len(row) != n for row in costs):
        raise ValueError("Число задач должно совпадать с числом агентов.")
    if any(type(c) is not int or c <= 0 for row in costs for c in row):
        raise ValueError("Все стоимости должны быть положительными целыми.")


@dataclass
class Outcome:
    # assignment[i] = индекс задачи, выбранной для агента i. Индексы с нуля.
    assignment: list[int]
    messages: list[Message] = field(default_factory=list)
    # None в метрике messages означает: обмен данными baseline не моделируется.
    communication_modelled: bool = True


@dataclass
class Contractor:
    """Исполнитель видит только свою строку стоимости.

    Менеджер вызывает propose/accept и НЕ читает _costs напрямую.
    Это логическая изоляция, а не защищённая многопроцессная среда.
    """
    agent_id: int
    _costs: tuple[int, ...]
    assigned_task: Optional[int] = None

    def propose(self, task: int) -> Optional[int]:
        if not 0 <= task < len(self._costs):
            raise ValueError("Неверный индекс задачи.")
        return None if self.assigned_task is not None else self._costs[task]

    def accept(self, task: int) -> None:
        if self.assigned_task is not None:
            raise ValueError("Исполнитель уже занят.")
        if not 0 <= task < len(self._costs):
            raise ValueError("Неверный индекс задачи.")
        self.assigned_task = task


def make_contractors(costs: Matrix) -> list[Contractor]:
    validate_costs(costs)
    return [Contractor(i, tuple(row)) for i, row in enumerate(costs)]


def validate_order(order: list[int], n: int) -> None:
    if (len(order) != n or any(type(x) is not int for x in order)
            or sorted(order) != list(range(n))):
        raise ValueError("Порядок задач должен быть перестановкой 0..n-1.")


def exact(costs: Matrix) -> Outcome:
    """Полный перебор назначений: только малые n, не промышленный solver."""
    validate_costs(costs)
    n = len(costs)
    if n > 8:
        raise ValueError("Полный перебор ограничен n <= 8.")
    # permutations выдаёт лексикографический порядок; он разрешает ничьи.
    best = min(permutations(range(n)),
               key=lambda p: sum(costs[i][p[i]] for i in range(n)))
    return Outcome(list(best), communication_modelled=False)


def evaluate(costs: Matrix, out: Outcome, optimal_cost: int) -> dict[str, object]:
    """Невалидное назначение НЕ получает cost/gap, даже если сумма мала."""
    validate_costs(costs)
    n = len(costs)
    if not isinstance(out, Outcome):
        raise TypeError("Алгоритм должен возвращать Outcome.")
    a = out.assignment
    if (len(a) != n or any(type(t) is not int or not 0 <= t < n for t in a)):
        raise ValueError("assignment должен содержать n допустимых индексов задач.")
    distinct = len(set(a))
    feasible = distinct == n
    proposal_cost = sum(costs[i][a[i]] for i in range(n))
    return {
        'feasible': feasible,
        'cost': proposal_cost if feasible else None,
        'proposal_cost': proposal_cost,
        'conflicts': n - distinct,
        'coverage': distinct / n,
        'optimal_cost': optimal_cost,
        'gap_pct': 100.0 * (proposal_cost - optimal_cost) / optimal_cost if feasible else None,
        'messages': len(out.messages) if out.communication_modelled else None,
        'assignment': a,
    }
