"""Готовый автомат агента; студент правит только policy.py."""
from copy import deepcopy


class BookingEngine:
    def __init__(self, store, mcp, policy):
        self.store, self.mcp, self.policy = store, mcp, policy
        self.active = {}  # Локальное состояние живого процесса; пропадет при перезапуске.

    async def handle(self, user_id, task_id, context_id, message_id, payload):
        key = self.policy.checkpoint_key(user_id, task_id)
        state = deepcopy(self.active.get(key) or self.store.load_checkpoint(key) or {})
        defaults = dict(user_id=user_id, task_id=task_id, context_id=context_id,
                        requirements={}, phase='search', proposal=None, reservation=None,
                        chat=[], cache={})
        defaults.update(state)
        state = defaults
        profile = await self.mcp.read_resource(f'profile://{user_id}')
        remembered = self.policy.memory_to_save(profile, payload.get('remember'), message_id)
        if remembered != profile:
            profile = await self.mcp.call_tool('save_preference', {'user_id': user_id, 'profile': remembered})
        requirements = self.policy.compose_requirements(
            state['requirements'], payload.get('patch', {}), profile)
        if requirements != state['requirements']:
            state.update(phase='search', proposal=None, reservation=None)
        state['requirements'] = requirements
        missing = [k for k in ('date', 'time', 'people') if not requirements.get(k)]
        if missing:
            state['phase'] = 'need_input'
            text = 'Уточните: ' + ', '.join(missing)
        elif payload.get('confirm') and state['phase'] == 'waiting_confirmation' and state['proposal']:
            result = await self.mcp.call_tool('reserve_room', {
                'user_id': user_id, 'task_id': task_id, 'room_id': state['proposal']['id'],
                'requirements': requirements})
            state = self.policy.after_reservation(state, result)
            text = 'Бронирование выполнено.' if state['phase'] == 'completed' else 'Вариант уже занят; ищу замену.'
        else:
            text = 'Ожидаю подтверждения.'
        if not missing and state['phase'] in ('search', 'need_input'):
            rooms = await self.mcp.call_tool('search_rooms', {'requirements': requirements})
            state['cache'] = {'last_search': rooms}
            if rooms:
                state.update(phase='waiting_confirmation', proposal=rooms[0], reservation=None)
                text = f"Подходит {rooms[0]['id']}. Подтвердите бронирование."
            else:
                state.update(phase='need_input', proposal=None, reservation=None)
                text = 'Свободных подходящих аудиторий нет. Измените условия.'
        state['chat'].append({'message_id': message_id, 'payload': deepcopy(payload)})
        self.active[key] = deepcopy(state)
        self.store.save_checkpoint(key, self.policy.checkpoint_to_save(state))
        return {**{k: deepcopy(state[k]) for k in (
            'user_id', 'task_id', 'context_id', 'phase', 'requirements', 'proposal', 'reservation')}, 'text': text}
