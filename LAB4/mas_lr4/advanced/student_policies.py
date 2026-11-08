"""Bounded workflows: fixed <=28 calls; coordinator <=40 calls.

All roles share Engine budgets. Role prose is distinct from verified reports.
Kept self-contained so each engine's freeze captures the complete policy.
"""
import json


def _instruction(text, **feedback):
    return text + "\n" + json.dumps(feedback, ensure_ascii=False)


def _handoff(handoff):
    """Forward role prose and artifact identity; Engine supplies current tests.

    Never carry an old verified_report as if it described the current artifact.
    Full current reports and source are already included in every Engine context.
    """
    return {key: value for key, value in handoff.items()
            if key != 'verified_report'}


def fixed(engine):
    """Always programmer -> reviewer -> programmer -> independent finish."""
    draft = engine.run_role(
        'programmer',
        'Исправь артефакт по условию общим алгоритмом. Используй инструменты '
        'этого типа задачи, проверь результат и передай вывод через yield.',
        max_turns=10)
    review = engine.run_role(
        'reviewer',
        _instruction(
            'Проверь текущий артефакт, контракт и крайние случаи. Менять код '
            'или ответ нельзя. Используй реальные проверки; передай конкретные '
            'замечания через yield. Слова автора не подтверждают прохождение.',
            draft=_handoff(draft)),
        max_turns=6)
    engine.run_role(
        'programmer',
        _instruction(
            'Заключительный этап: учти замечания ревьюера, исправь дефекты и '
            'проверь результат. Если замечание необоснованно, объясни почему. '
            'Не подставляй ответы открытых примеров.',
            review=_handoff(review)),
        max_turns=12)
    engine.finish()


def _decision_error(decision):
    """Validate exact schemas before any delegation."""
    if type(decision) is not dict:
        return 'Решение должно быть JSON-объектом.'
    if decision.get('action') == 'finish':
        return None if set(decision) == {'action'} else 'finish: только поле action.'
    if decision.get('action') != 'delegate':
        return 'Допустимые action: delegate или finish.'
    if set(decision) != {'action', 'role', 'instruction'}:
        return 'delegate: ровно action, role, instruction.'
    if type(decision['role']) is not str or decision['role'] not in ('developer', 'tester'):
        return 'Допустимые роли: developer или tester.'
    if type(decision['instruction']) is not str or len(decision['instruction']) > 6000:
        return 'instruction: строка длиной не более 6000 символов.'
    return None


def coordinator(engine):
    """Up to 10 routing decisions and 3 role actions per delegation."""
    feedback = {
        'instruction': 'Выбирай developer для исправлений или tester для '
        'проверки. Сам артефакт не редактируй. Максимум 10 решений, до 3 '
        'действий исполнителя за этап; общий бюджет включает координацию. '
        'Для завершения выбери finish. Актуальный отчёт проверки находится '
        'в контексте Engine; слова исполнителя не подтверждают успех.'}
    for route in range(10):
        decision = engine.coordinator_decision(feedback)
        error = _decision_error(decision)
        if error:
            feedback = {'error': error}
        elif decision['action'] == 'finish':
            if engine.finish():
                return
            feedback = {
                'error': 'Финальная проверка не пройдена. Организуй исправление. '
                'Актуальный отчёт находится в контексте Engine.'}
        else:
            role = decision['role']
            handoff = engine.run_role(
                role,
                _instruction(
                    decision['instruction'],
                    role_rules=(
                        'Исправляй артефакт инструментами, проверь результат, '
                        'передай вывод через yield.' if role == 'developer' else
                        'Артефакт менять нельзя. Проверь контракт и тесты, '
                        'передай конкретные замечания через yield.')),
                max_turns=3)
            feedback = {
                'role': role, 'handoff': _handoff(handoff)}
        feedback['decisions_remaining'] = 9 - route
