"""Готовые клиенты MCP и A2A и запуск двух локальных процессов."""
import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from mcp import Client as MCPClient
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.helpers.proto_helpers import get_data_parts, new_data_message
from a2a.types.a2a_pb2 import GetTaskRequest, Role, SendMessageRequest, TaskState
from google.protobuf.json_format import MessageToDict

from .db import WorldStore


def trace(path, event, **data):
    with Path(path).open('a', encoding='utf-8') as handle:
        handle.write(json.dumps({'at': datetime.now(timezone.utc).isoformat(),
                                 'event': event, **data}, ensure_ascii=False) + '\n')


class MCPAdapter:
    def __init__(self, client, trace_path):
        self.client, self.trace_path = client, trace_path

    async def call_tool(self, name, arguments):
        result = await self.client.call_tool(name, arguments)
        if result.is_error:
            raise RuntimeError(f'MCP {name}: {result.content}')
        value = result.structured_content
        if value is None:
            value = json.loads(''.join(p.text for p in result.content if p.type == 'text'))
        trace(self.trace_path, 'mcp.tool.call', name=name, arguments=arguments, result=value)
        # SDK оборачивает возвращаемый список в structuredContent.result.
        if name == 'search_rooms' and isinstance(value, dict) and 'result' in value:
            return value['result']
        return value

    async def read_resource(self, uri):
        result = await self.client.read_resource(uri)
        value = json.loads(''.join(p.text for p in result.contents if hasattr(p, 'text')))
        trace(self.trace_path, 'mcp.resource.read', uri=uri, result=value)
        return value

    async def discover(self):
        tools = await self.client.list_tools()
        resources = await self.client.list_resources()
        templates = await self.client.list_resource_templates()
        result = {'protocol_version': self.client.protocol_version,
                  'tools': [item.name for item in tools.tools],
                  'resources': [str(item.uri) for item in resources.resources],
                  'resource_templates': [item.uri_template for item in templates.resource_templates]}
        trace(self.trace_path, 'mcp.discover', **result)
        return result


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class ProtocolLab:
    def __init__(self, root_dir: Path, policy_path=None, work_dir=None):
        self.root_dir = Path(root_dir).resolve()
        self.policy_path = Path(policy_path or self.root_dir / 'lab' / 'policy.py').resolve()
        self.work_dir = Path(work_dir or tempfile.mkdtemp(prefix='mas-lab-')).resolve()
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.trace_path = self.work_dir / 'trace.jsonl'
        self.db_path = self.work_dir / 'world.sqlite'
        self.world = WorldStore(self.db_path)
        self.mcp_port, self.a2a_port = free_port(), free_port()
        self.mcp_url = f'http://127.0.0.1:{self.mcp_port}/mcp'
        self.a2a_url = f'http://127.0.0.1:{self.a2a_port}'
        self.processes, self.logs = {}, []
        self.http, self.client = None, None
        self.discovery = {}

    def _start(self, role):
        log = (self.work_dir / f'{role}.log').open('ab')
        self.logs.append(log)
        command = [sys.executable, '-m', 'lab.protocol_worker', role,
                   '--port', str(self.mcp_port if role == 'mcp' else self.a2a_port),
                   '--db', str(self.db_path), '--trace', str(self.trace_path),
                   '--policy', str(self.policy_path), '--mcp-url', self.mcp_url]
        self.processes[role] = subprocess.Popen(
            command, cwd=self.root_dir, stdout=log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONUNBUFFERED': '1'})

    async def _ready(self, role):
        url = self.mcp_url if role == 'mcp' else self.a2a_url + '/.well-known/agent-card.json'
        deadline = time.monotonic() + 30
        async with httpx.AsyncClient(timeout=1, trust_env=False) as probe:
            while time.monotonic() < deadline:
                if self.processes[role].poll() is not None:
                    raise RuntimeError(f'Процесс {role} завершился. См. {self.work_dir / (role + ".log")}')
                try:
                    async with probe.stream('GET', url) as response:
                        if (role == 'mcp' and response.status_code < 500) or response.status_code == 200:
                            return
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.1)
        raise TimeoutError(f'Сервис {role} не запустился за 30 секунд.')

    async def _connect_a2a(self):
        self.http = httpx.AsyncClient(timeout=30, trust_env=False)
        card = await A2ACardResolver(self.http, self.a2a_url).get_agent_card()
        trace(self.trace_path, 'a2a.card', card=MessageToDict(card))
        self.discovery['a2a'] = MessageToDict(card)
        self.client = ClientFactory(ClientConfig(streaming=False, httpx_client=self.http)).create(card)

    async def __aenter__(self):
        try:
            self._start('mcp')
            await self._ready('mcp')
            async with MCPClient(self.mcp_url, cache=None) as client:
                adapter = MCPAdapter(client, self.trace_path)
                self.discovery['mcp'] = await adapter.discover()
                await adapter.read_resource('rules://booking')
            self._start('a2a')
            await self._ready('a2a')
            await self._connect_a2a()
            return self
        except BaseException:
            await self.__aexit__(None, None, None)
            raise

    async def __aexit__(self, *_):
        if self.client:
            await self.client.close()
        if self.http:
            await self.http.aclose()
        for process in self.processes.values():
            if process.poll() is None:
                process.terminate()
                try:
                    await asyncio.to_thread(process.wait, 5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    await asyncio.to_thread(process.wait, 5)
        for log in self.logs:
            log.close()

    async def restart_booking_agent(self):
        old_pid = self.processes['a2a'].pid
        await self.client.close()
        await self.http.aclose()
        process = self.processes['a2a']
        process.terminate()
        await asyncio.to_thread(process.wait, 5)
        self._start('a2a')
        await self._ready('a2a')
        await self._connect_a2a()
        trace(self.trace_path, 'agent.restart', old_pid=old_pid, new_pid=self.processes['a2a'].pid,
              persisted_database=str(self.db_path))

    @staticmethod
    def _decode(task):
        values = get_data_parts(task.status.message.parts)
        result = values[0] if values else {}
        return {**result, 'task_id': task.id, 'context_id': task.context_id,
                'a2a_state': TaskState.Name(task.status.state),
                'application_task_id': result.get('task_id'),
                'application_context_id': result.get('context_id'),
                'status_data': values,
                'artifact_count': len(task.artifacts),
                'artifacts': [MessageToDict(artifact) for artifact in task.artifacts]}

    async def send(self, user_id, payload, task_id=None, context_id=None):
        message = new_data_message({'user_id': user_id, 'payload': payload},
                                   context_id=context_id, task_id=task_id, role=Role.ROLE_USER,
                                   media_type='application/json')
        trace(self.trace_path, 'a2a.send', message=MessageToDict(message))
        task = None
        async for response in self.client.send_message(SendMessageRequest(message=message)):
            if response.HasField('task'):
                task = response.task
        if task is None:
            raise RuntimeError('A2A не вернул Task.')
        result = self._decode(task)
        trace(self.trace_path, 'a2a.result', result=result)
        return result

    async def get_task(self, task_id):
        task = await self.client.get_task(GetTaskRequest(id=task_id))
        result = self._decode(task)
        trace(self.trace_path, 'a2a.get', task_id=task_id, result=result)
        return result

    async def inspect_protocols(self):
        return self.discovery
