"""Шесть обязательных сценариев: реальные запросы MCP/A2A, без вызовов LLM."""
import json
from pathlib import Path

from .contracts import (check_checkpoint, check_key, check_memory, check_requirements,
                        check_reservation_transition, load_policy)
from .db import ROOMS
from .protocols import ProtocolLab

INPUT = 'TASK_STATE_INPUT_REQUIRED'
COMPLETED = 'TASK_STATE_COMPLETED'


def require(condition, explanation):
    if not condition:
        raise AssertionError(explanation)


def request(day=1, building='A', time='10:00'):
    return {'date': f'2026-11-{day:02d}', 'time': time, 'people': 20,
            'projector': True, 'building': building}


async def continuation(lab, response, user='alice', **payload):
    return await lab.send(user, payload, task_id=response['task_id'], context_id=response['context_id'])


async def check_completed(lab, response, user, expected):
    task = await lab.get_task(response['task_id'])
    require(response['phase'] == task['phase'] == 'completed'
            and response['a2a_state'] == task['a2a_state'] == COMPLETED,
            f"Ожидалась завершенная задача; получено {response.get('phase')} / {task['a2a_state']}.")
    actual = [row for row in lab.world.reservations() if row['task_id'] == response['task_id']]
    require(len(actual) == 1, 'Завершенная задача должна соответствовать ровно одной записи в базе броней.')
    actual = actual[0]
    fields = ('id', 'room_id', 'date', 'time', 'user_id')
    receipt = {field: actual[field] for field in fields}
    require(actual['user_id'] == user and actual['task_id'] == expected['task_id'],
            'Бронь записана не для ожидаемого пользователя или задачи.')
    for label, observed in (('SendMessage', response), ('GetTask', task)):
        require(observed.get('user_id') == user
                and observed['task_id'] == observed['application_task_id'] == expected['task_id']
                and observed['context_id'] == observed['application_context_id'] == expected['context_id'],
                f'{label}: идентификаторы прикладного результата не совпадают с протокольной Task и исходной заявкой.')
        require(observed.get('requirements') == expected['requirements']
                and observed.get('proposal') in (None, expected['proposal']),
                f'{label}: завершение изменило требования или содержит неподтвержденное предложение.')
        require(observed.get('reservation') == receipt,
                f'{label}: поля id, room_id, date, time, user_id результата не совпадают с SQLite.')
        require(len(observed['status_data']) == 1 and observed['status_data'][0].get('reservation') == receipt,
                f'{label}: данные статуса должны содержать ту же фактическую бронь.')
        require(observed['artifact_count'] == 1 and len(observed['artifacts']) == 1,
                f'{label}: завершение должно иметь один артефакт с реальной бронью.')
        parts = observed['artifacts'][0].get('parts', [])
        data_parts = [part['data'] for part in parts if 'data' in part]
        require(data_parts == [receipt],
                f'{label}: содержимое артефакта не совпадает с результатом и SQLite по всем полям брони.')
    require(response['artifacts'] == task['artifacts'], 'SendMessage и GetTask вернули разные артефакты.')
    requirements, proposal = expected['requirements'], expected['proposal']
    require(actual['room_id'] == proposal['id'] and actual['date'] == requirements['date']
            and actual['time'] == requirements['time'],
            'Фактическая бронь не соответствует подтвержденной аудитории, дате или времени.')
    room = next((room for room in ROOMS if room['id'] == actual['room_id']), None)
    require(room is not None and proposal == room and room['capacity'] >= requirements['people']
            and (not requirements.get('projector') or room['projector'])
            and (not requirements.get('building') or room['building'] == requirements['building']),
            'Подтвержденное предложение не соответствует каталогу или актуальным требованиям.')
    return actual


async def scenario_1(lab):
    initial = request()
    del initial['time']
    first = await lab.send('alice', {'patch': initial})
    require(first['phase'] == 'need_input' and first['a2a_state'] == INPUT,
            'Неполная заявка должна перевести ту же A2A Task в input-required.')
    second = await continuation(lab, first, patch={'time': '10:00'})
    require(second['requirements'] == request() and second['phase'] == 'waiting_confirmation',
            'Уточнение времени потеряло уже известные поля заявки. Проверьте compose_requirements.')
    require(second['task_id'] == first['task_id'] and second['artifact_count'] == 0,
            'Уточнение создало новую задачу или преждевременный артефакт.')
    final = await continuation(lab, second, confirm=True)
    await check_completed(lab, final, 'alice', second)
    check_requirements(load_policy(lab.policy_path))
    return 'Уточнение продолжает Task; бронь появляется только после подтверждения.'


async def scenario_2(lab):
    first = await lab.send('alice', {'patch': request(2)})
    require(first['phase'] == 'waiting_confirmation', 'Не удалось подготовить предложение.')
    pid = lab.processes['a2a'].pid
    await lab.restart_booking_agent()
    require(pid != lab.processes['a2a'].pid, 'Процесс агента фактически не перезапустился.')
    restored = await lab.get_task(first['task_id'])
    require(restored['a2a_state'] == INPUT and restored['task_id'] == first['task_id'],
            'Протокольная Task не пережила перезапуск.')
    final = await continuation(lab, first, confirm=True)
    require(final['phase'] == 'completed',
            'После перезапуска «подтверждаю» не завершило исходную заявку. Нужен полный checkpoint, не только требования.')
    actual = await check_completed(lab, final, 'alice', first)
    require(actual['room_id'] == first['proposal']['id'], 'Подтвержден не сохраненный вариант.')
    check_checkpoint(load_policy(lab.policy_path))
    return 'Новый процесс восстановил прикладной снимок и завершил исходную Task.'


async def scenario_3(lab):
    first = await lab.send('alice', {'patch': request(3, 'B'), 'remember': {'building': 'B'}})
    await check_completed(lab, await continuation(lab, first, confirm=True), 'alice', first)
    # Новый процесс теряет active/cache; A2A history сохраняется отдельно, но автомат ее не читает.
    await lab.restart_booking_agent()
    new_request = request(4)
    del new_request['building']
    second = await lab.send('alice', {'patch': new_request})
    require(second['context_id'] != first['context_id'] and second['task_id'] != first['task_id'],
            'Новая заявка должна иметь новый контекст и Task.')
    profile = lab.world.read_profile('alice')
    require(profile.get('building') == 'B' and profile.get('source_message_id') and profile.get('revision') == 1,
            'Явная просьба запомнить корпус не сохранилась вместе с источником и версией.')
    require(second['proposal']['building'] == 'B', 'Новый диалог не использовал долговременную память.')
    await check_completed(lab, await continuation(lab, second, confirm=True), 'alice', second)
    check_memory(load_policy(lab.policy_path))
    return 'Предпочтение сохранилось между задачами и процессами без старой истории.'


async def scenario_4(lab):
    # Фикстура: профиль уже существовал до запуска текущего диалога.
    original = {'building': 'B', 'source_message_id': 'explicit-old-message', 'revision': 7}
    lab.world.write_profile('alice', original)
    first = await lab.send('alice', {'patch': request(5, 'A')})
    require(first['proposal']['building'] == 'A',
            'Разовое явное требование A должно иметь приоритет над сохраненным предпочтением B.')
    final = await continuation(lab, first, confirm=True)
    actual = await check_completed(lab, final, 'alice', first)
    require(actual['room_id'].startswith('A-'), 'Создана бронь не в требуемом корпусе.')
    require(lab.world.read_profile('alice') == original, 'Разовое требование изменило долговременную память.')
    return 'Разовое исключение переопределило память для задачи и не переписало профиль.'


async def scenario_5(lab):
    a = await lab.send('alice', {'patch': request(6, 'A')}, context_id='shared-conversation')
    b = await lab.send('bob', {'patch': request(7, 'B')}, context_id='bob-conversation')
    c = await lab.send('alice', {'patch': request(8, 'B')}, context_id='shared-conversation')
    require(a['task_id'] != c['task_id'] and a['context_id'] == c['context_id'],
            'Две задачи одного диалога должны различаться taskId.')
    for user, started, expected in [('alice', a, request(6, 'A')), ('bob', b, request(7, 'B')),
                                    ('alice', c, request(8, 'B'))]:
        final = await continuation(lab, started, user=user, confirm=True)
        require(final['requirements'] == expected and final['user_id'] == user,
                'Перемешанные задачи перезаписали друг друга. Проверьте ключ (user_id, task_id).')
        actual = await check_completed(lab, final, user, started)
        require(actual['date'] == expected['date'] and actual['room_id'].startswith(expected['building'] + '-'),
                'Подтверждение использовало данные соседней задачи.')
    check_key(load_policy(lab.policy_path))
    return 'Два пользователя и две задачи одного пользователя сохранили независимые состояния.'


async def scenario_6(lab):
    first = await lab.send('alice', {'patch': request(9)})
    lost_room = first['proposal']['id']
    lab.world.occupy(lost_room, '2026-11-09', '10:00')
    second = await continuation(lab, first, confirm=True)
    task = await lab.get_task(first['task_id'])
    require(second['phase'] == 'waiting_confirmation' and task['a2a_state'] == INPUT
            and second.get('reservation') is None and task['artifact_count'] == 0,
            'Неуспешная бронь не завершает задачу: очистите старое предложение и вернитесь к поиску.')
    require(second['proposal'] and second['proposal']['id'] != lost_room,
            'Нужна новая свободная аудитория вместо устаревшего варианта.')
    require(not [r for r in lab.world.reservations() if r['user_id'] == 'alice'],
            'Новая аудитория забронирована без нового подтверждения пользователя.')
    final = await continuation(lab, second, confirm=True)
    actual = await check_completed(lab, final, 'alice', second)
    require(actual['room_id'] != lost_room, 'Результат не соответствует новому предложению.')
    check_reservation_transition(load_policy(lab.policy_path))
    return 'Фактический отказ инструмента вызвал новое предложение и новое подтверждение.'


SCENARIOS = [
    ('Не хватает данных', scenario_1), ('Перезапуск на паузе', scenario_2),
    ('Новый диалог', scenario_3), ('Разовое исключение', scenario_4),
    ('Перемешанные обращения', scenario_5), ('Сведения устарели', scenario_6),
]


async def run_suite(root_dir, output_dir, policy_path=None, selected=None):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for number, (name, scenario) in enumerate(SCENARIOS, 1):
        if selected and number != selected:
            continue
        print(f'{number}. {name} …', flush=True)
        work_dir = output_dir / f'scenario_{number}'
        record = {'scenario': number, 'name': name, 'passed': False,
                  'trace': str(work_dir / 'trace.jsonl')}
        try:
            async with ProtocolLab(root_dir, policy_path, work_dir) as lab:
                record['message'] = await scenario(lab)
                record['passed'] = True
                record['protocols'] = await lab.inspect_protocols()
        except AssertionError as error:
            record['message'] = str(error)
        except Exception as error:
            record['message'] = f'Ошибка запуска или реализации: {type(error).__name__}: {error}'
        results.append(record)
        print(f"   {'PASS' if record['passed'] else 'FAIL'} — {record['message']}", flush=True)
    report = {'passed': sum(r['passed'] for r in results), 'total': len(results), 'results': results}
    (output_dir / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nРезультат: {report['passed']}/{report['total']}. Файлы: {output_dir}", flush=True)
    return report
