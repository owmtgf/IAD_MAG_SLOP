"""Готовые серверы официальных SDK. Запускаются автоматически через run_lab.py."""
import argparse
import importlib.util
import json
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from mcp import Client as MCPClient
from mcp.server import MCPServer
from starlette.applications import Starlette
from a2a.helpers.proto_helpers import (get_data_parts, new_data_message, new_data_part,
                                       new_task_from_user_message)
from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks import TaskStore, TaskUpdater
from a2a.types.a2a_pb2 import (AgentCapabilities, AgentCard, AgentInterface, AgentSkill,
                              ListTasksResponse, Task, TaskState)
from a2a.utils.constants import PROTOCOL_VERSION_CURRENT, TransportProtocol
from a2a.utils.errors import UnsupportedOperationError

from .db import WorldStore
from .protocols import MCPAdapter
from .runtime import BookingEngine


class SQLiteTaskStore(TaskStore):
    """Долговечные протокольные Task. Отдельны от снимков прикладного автомата."""
    def __init__(self, path):
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS protocol_tasks (id TEXT PRIMARY KEY, data BLOB)')

    async def save(self, task, context):
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT OR REPLACE INTO protocol_tasks VALUES (?,?)',
                       (task.id, task.SerializeToString()))

    async def get(self, task_id, context):
        with sqlite3.connect(self.path) as db:
            row = db.execute('SELECT data FROM protocol_tasks WHERE id=?', (task_id,)).fetchone()
        return Task.FromString(row[0]) if row else None

    async def list(self, params, context):
        # Лаба использует GetTask, а не ListTasks; неподдерживаемое явно отклоняем.
        raise UnsupportedOperationError('В учебном сервере доступен GetTask, но не ListTasks.')

    async def delete(self, task_id, context):
        with sqlite3.connect(self.path) as db:
            db.execute('DELETE FROM protocol_tasks WHERE id=?', (task_id,))


def mcp_app(store):
    server = MCPServer('Room catalog', version='1.0', log_level='WARNING')

    @server.tool()
    def search_rooms(requirements: dict) -> list[dict]:
        """Найти свободные аудитории по требованиям date, time, people, projector, building."""
        return store.search_rooms(requirements)

    @server.tool()
    def reserve_room(user_id: str, task_id: str, room_id: str, requirements: dict) -> dict:
        """Атомарно создать бронь или вернуть occupied. Вызывать после подтверждения."""
        return store.reserve_room(user_id, task_id, room_id, requirements)

    @server.tool()
    def save_preference(user_id: str, profile: dict) -> dict:
        """Сохранить явно заданное предпочтение с источником и версией."""
        return store.write_profile(user_id, profile)

    @server.resource('profile://{user_id}', mime_type='application/json')
    def profile(user_id: str) -> str:
        """Долговременные предпочтения одного пользователя."""
        return json.dumps(store.read_profile(user_id), ensure_ascii=False)

    @server.resource('rules://booking', mime_type='application/json')
    def rules() -> str:
        """Правила: бронь только после подтверждения; слоты фиксированы."""
        return json.dumps({'required': ['date', 'time', 'people'], 'confirmation_required': True,
                           'buildings': ['A', 'B'], 'slot_minutes': 90,
                           'source_of_truth': 'reservation tool result'})

    return server.streamable_http_app(json_response=True, stateless_http=True)


def a2a_app(args, store):
    specification = importlib.util.spec_from_file_location('student_policy', args.policy)
    policy = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(policy)
    card = AgentCard(
        name='Seminar room booking agent', description='Находит и бронирует учебные аудитории.',
        version='1.0', capabilities=AgentCapabilities(streaming=False),
        supported_interfaces=[AgentInterface(url=f'http://127.0.0.1:{args.port}/a2a',
            protocol_binding=TransportProtocol.JSONRPC, protocol_version=PROTOCOL_VERSION_CURRENT)],
        default_input_modes=['application/json'], default_output_modes=['application/json'],
        skills=[AgentSkill(id='book-room', name='Бронирование аудитории',
            description='Заявка → уточнение → предложение → подтверждение → бронь.',
            tags=['booking', 'state', 'memory'])])

    class Executor(AgentExecutor):
        engine = None

        async def execute(self, context, event_queue):
            incoming = get_data_parts(context.message.parts)[0]
            if not context.current_task:
                await event_queue.enqueue_event(new_task_from_user_message(context.message))
            updater = TaskUpdater(event_queue, context.task_id, context.context_id)
            await updater.start_work()
            result = await self.engine.handle(incoming['user_id'], context.task_id,
                                             context.context_id, context.message.message_id,
                                             incoming['payload'])
            message = new_data_message(result, task_id=context.task_id,
                                       context_id=context.context_id, media_type='application/json')
            if result['phase'] == 'completed':
                await updater.add_artifact([new_data_part(result['reservation'])], name='reservation')
                await updater.complete(message)
            else:
                await updater.update_status(TaskState.TASK_STATE_INPUT_REQUIRED, message=message)

        async def cancel(self, context, event_queue):
            await TaskUpdater(event_queue, context.task_id, context.context_id).update_status(
                TaskState.TASK_STATE_CANCELED)

    executor = Executor()
    handler = DefaultRequestHandler(executor, SQLiteTaskStore(args.db), card)

    @asynccontextmanager
    async def lifespan(app):
        async with MCPClient(args.mcp_url, cache=None) as client:
            adapter = MCPAdapter(client, args.trace)
            await adapter.discover()
            await adapter.read_resource('rules://booking')
            executor.engine = BookingEngine(store, adapter, policy)
            yield

    return Starlette(routes=create_agent_card_routes(card) + create_jsonrpc_routes(handler, '/a2a'),
                     lifespan=lifespan)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('role', choices=['mcp', 'a2a'])
    parser.add_argument('--port', type=int, required=True)
    for name in ('db', 'trace', 'policy', 'mcp-url'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    store = WorldStore(args.db)
    app = mcp_app(store) if args.role == 'mcp' else a2a_app(args, store)
    uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='warning', access_log=False)


if __name__ == '__main__':
    main()
