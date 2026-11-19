"""Исправьте только пять функций. Готовые функции запускаются, но содержат ошибки.

Каждая функция должна возвращать независимую копию, не менять аргументы.
Инфраструктуру, сценарии и схему данных менять не требуется.
"""
from copy import deepcopy
import json


def compose_requirements(current: dict, patch: dict, memory: dict) -> dict:
    """TODO 1. Определите требования для текущей заявки.

    current — известные условия заявки, patch — поля из новой реплики,
    memory — профиль пользователя. Словари могут быть пустыми.
    Результат — словарь требований с полями из схемы в README.
    Правила согласования данных выведите из ситуаций 1, 3 и 4.
    """
    # A request is refined in place: known task conditions stay valid until a
    # later message explicitly replaces them.  A saved preference merely fills
    # in an omitted building and never overrides the current request.
    result = deepcopy(current)
    if "building" not in result and memory.get("building") in ("A", "B"):
        result["building"] = memory["building"]
    result.update(deepcopy(patch))
    result.setdefault("projector", False)
    return result


def memory_to_save(existing: dict, remember: dict | None,
                   source_message_id: str) -> dict:
    """TODO 2. Определите профиль, который должен остаться после обращения.

    existing — прежний профиль; remember — выделенная из реплики инструкция
    о запоминании (dict или None), в том числе пустая или недопустимая.
    source_message_id — идентификатор текущего сообщения.
    Результат — профиль по схеме README. Рассмотрите ситуации 3 и 4.
    """
    if not isinstance(remember, dict) or remember.get("building") not in ("A", "B"):
        return deepcopy(existing)
    return {
        "building": remember["building"],
        "source_message_id": source_message_id,
        "revision": existing.get("revision", 0) + 1,
    }


def checkpoint_key(user_id: str, task_id: str) -> str:
    """TODO 3. Выберите ключ для сохранения и загрузки снимка задачи.

    user_id и task_id — строки; внутри допустимы ':' и другие разделители.
    Результат — строка, используемая хранилищем при каждом обращении к снимку.
    Требования к этому ключу следуют из ситуаций 2 и 5.
    """
    # JSON preserves the boundaries of arbitrary opaque strings, unlike a
    # delimiter-based key such as ``user_id + ':' + task_id``.
    return json.dumps([user_id, task_id], ensure_ascii=False, separators=(",", ":"))


def checkpoint_to_save(state: dict) -> dict:
    """TODO 4. Определите содержимое сохраняемого снимка.

    state — словарь текущего состояния; смысл всех его полей описан в README.
    Результат — словарь, который инфраструктура записывает в SQLite как JSON
    и загружает после потери локального состояния процесса.
    Выберите состав снимка, опираясь на назначение данных и ситуацию 2.
    """
    return {key: deepcopy(state[key]) for key in (
        "user_id", "task_id", "context_id", "requirements", "phase", "proposal", "reservation",
    )}


def after_reservation(state: dict, result: dict) -> dict:
    """TODO 5. Определите состояние после попытки бронирования.

    state — текущее состояние задачи по схеме README.
    result имеет вид {'ok': True, 'reservation': {...}} либо
    {'ok': False, 'reason': 'occupied'}. Поля брони: id, room_id, date,
    time, user_id. Результат функции — новый словарь состояния той же схемы.
    Инфраструктура выбирает следующий шаг по phase; рассуждайте по ситуации 6.
    """
    updated = deepcopy(state)
    if result.get("ok"):
        updated["phase"] = "completed"
        updated["reservation"] = deepcopy(result["reservation"])
    else:
        # The offered room is no longer valid.  The runtime will perform a
        # fresh search when it sees the search phase.
        updated.update(phase="search", proposal=None, reservation=None)
    return updated
