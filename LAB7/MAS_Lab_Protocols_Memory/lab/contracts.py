"""Проверки уже заданных контрактов пяти функций внутри шести сценариев."""
import importlib.util
from copy import deepcopy


def load_policy(path):
    specification = importlib.util.spec_from_file_location('checked_student_policy', path)
    policy = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(policy)
    return policy


def require(condition, explanation):
    if not condition:
        raise AssertionError(explanation)


def mutable_ids(value):
    """Независимая копия не разделяет изменяемые объекты с аргументами."""
    if isinstance(value, dict):
        result = {id(value)}
        for item in value.values():
            result.update(mutable_ids(item))
        return result
    if isinstance(value, (list, set)):
        result = {id(value)}
        for item in value:
            result.update(mutable_ids(item))
        return result
    if isinstance(value, tuple):
        result = set()
        for item in value:
            result.update(mutable_ids(item))
        return result
    return set()


def clean_call(function, *arguments):
    before = deepcopy(arguments)
    result = function(*arguments)
    require(arguments == before, f'{function.__name__}: функция изменила входные данные.')
    require(not (mutable_ids(result) & mutable_ids(arguments)),
            f'{function.__name__}: изменение результата может затронуть входные данные — нарушена независимость данных.')
    return result


def check_requirements(policy):
    cases = [
        ({}, {}, {}, {'projector': False}),
        ({'date': '2026-11-01', 'people': 20, 'projector': True, 'building': 'A'},
         {'time': '10:00', 'projector': False, 'building': 'B'}, {'building': 'A'},
         {'date': '2026-11-01', 'time': '10:00', 'people': 20, 'projector': False, 'building': 'B'}),
        ({'people': 20, 'projector': False, 'building': 'A'}, {}, {'building': 'B'},
         {'people': 20, 'projector': False, 'building': 'A'}),
        ({'people': 20}, {}, {'building': 'B', 'people': 99, 'projector': True, 'time': '23:59'},
         {'people': 20, 'projector': False, 'building': 'B'}),
        ({'projector': False}, {'projector': True}, {}, {'projector': True}),
    ]
    for current, patch, memory, expected in cases:
        result = clean_call(policy.compose_requirements, current, patch, memory)
        require(result == expected,
                'compose_requirements: итоговые требования теряют условие заявки или противоречат уточнению, '
                'разовому исключению либо правилам данных. Сопоставьте ситуации 1, 3 и 4 с README.')
        require(type(result['projector']) is bool,
                'compose_requirements: projector должен оставаться логическим значением.')


def sample_state():
    return {'user_id': 'alice', 'task_id': 'task-1', 'context_id': 'conversation-1',
            'requirements': {'date': '2026-11-02', 'time': '10:00', 'people': 20,
                             'projector': False, 'building': 'A'},
            'phase': 'waiting_confirmation',
            'proposal': {'id': 'A-101', 'building': 'A', 'capacity': 24, 'projector': True},
            'reservation': None, 'chat': [{'message_id': 'm-1', 'payload': {'confirm': False}}],
            'cache': {'last_search': [{'id': 'A-101'}]}}


def check_checkpoint(policy):
    fields = {'user_id', 'task_id', 'context_id', 'requirements', 'phase', 'proposal', 'reservation'}
    pending = sample_state()
    completed = deepcopy(pending)
    completed.update(phase='completed', reservation={'id': 'r-1', 'room_id': 'A-101',
                     'date': '2026-11-02', 'time': '10:00', 'user_id': 'alice'})
    for state in (pending, completed):
        result = clean_call(policy.checkpoint_to_save, state)
        require(isinstance(result, dict) and set(result) == fields,
                'checkpoint_to_save: состав снимка не отделяет сведения для продолжения задачи '
                'от временной рабочей информации. Проверьте назначение полей state и ситуацию 2.')
        require(result == {key: state[key] for key in fields},
                'checkpoint_to_save: снимок искажает данные, необходимые для продолжения задачи.')


def check_memory(policy):
    existing = {}
    for building, source, revision in [('B', 'explicit-message-1', 1),
                                       ('A', 'explicit-message-2', 2),
                                       ('A', 'explicit-message-3', 3)]:
        result = clean_call(policy.memory_to_save, existing, {'building': building}, source)
        require(result == {'building': building, 'source_message_id': source, 'revision': revision},
                'memory_to_save: профиль не отражает явное обновление, его источник или историю изменений.')
        existing = result
    original = {'building': 'B', 'source_message_id': 'earlier-message', 'revision': 7}
    for instruction in (None, {}, {'building': 'C'}, {'building': None}, {'unrelated': 'A'}):
        result = clean_call(policy.memory_to_save, original, instruction, 'must-not-be-used')
        require(result == original,
                'memory_to_save: профиль изменился без допустимой инструкции на обновление.')
    updated = clean_call(policy.memory_to_save, original, {'building': 'A'}, 'actual-message')
    require(updated == {'building': 'A', 'source_message_id': 'actual-message', 'revision': 8},
            'memory_to_save: источник или счетчик обновлений не соответствует истории обращений.')


def check_key(policy):
    pairs = [('alice', 'same-task'), ('bob', 'same-task'), ('alice', 'another-task'),
             ('a', 'b:c'), ('a:b', 'c'), ('a', 'b|c'), ('a|b', 'c'),
             ('a', 'b/c'), ('a/b', 'c'), ('пользователь', 'задача:1')]
    keys = [policy.checkpoint_key(*pair) for pair in pairs]
    require(all(isinstance(key, str) for key in keys), 'checkpoint_key: результат должен быть строкой.')
    require(len(set(keys)) == len(pairs),
            'checkpoint_key: независимые заявки получили одинаковый ключ. '
            'Проверьте ситуацию 5 и допустимый формат идентификаторов.')
    require(keys == [policy.checkpoint_key(*pair) for pair in pairs],
            'checkpoint_key: повторный доступ к тому же снимку получил другой ключ.')


def check_reservation_transition(policy):
    state = sample_state()
    reservation = {'id': 'r-1', 'room_id': 'A-101', 'date': '2026-11-02',
                   'time': '10:00', 'user_id': 'alice'}
    result = clean_call(policy.after_reservation, state, {'ok': True, 'reservation': reservation})
    require(result.get('proposal') in (None, state['proposal']),
            'after_reservation: завершение содержит предложение, которое пользователь не подтверждал.')
    require(result.get('cache') in ({}, state['cache']),
            'after_reservation: кеш можно сохранить либо очистить; новую выдачу формирует поиск.')
    expected = deepcopy(state)
    expected.update(phase='completed', reservation=reservation,
                    proposal=deepcopy(result.get('proposal')), cache=deepcopy(result.get('cache')))
    require(result == expected,
            'after_reservation: состояние после успешного ответа не соответствует '
            'подтвержденному результату или данным исходной заявки.')
    result = clean_call(policy.after_reservation, state, {'ok': False, 'reason': 'occupied'})
    require(result.get('cache') in ({}, state['cache']),
            'after_reservation: кеш можно сохранить либо очистить; новую выдачу формирует поиск.')
    expected = deepcopy(state)
    expected.update(phase='search', proposal=None, reservation=None, cache=deepcopy(result.get('cache')))
    require(result == expected,
            'after_reservation: состояние после occupied не соответствует отсутствию брони '
            'и необходимости согласовать свободный вариант. Рассмотрите ситуацию 6.')
