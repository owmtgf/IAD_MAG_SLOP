"""Real isolated-worker checks for stdlib access and denied capabilities."""
import json
from pathlib import Path
import tempfile
import unittest

from advanced.executor import execute, probe


class SandboxRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / 'project'
        (self.project / 'app').mkdir(parents=True)
        (self.project / 'app/__init__.py').write_text('')

    def run_source(self, source, data=None):
        (self.project / 'app/api.py').write_text(source)
        result = execute(self.project, [data])
        self.assertNotIn('error', result, result)
        return result['results'][0]

    def test_doctor_probes_stdlib_in_worker(self):
        probe()

    def test_stdlib_dataclasses_and_decimal_are_readable(self):
        result = self.run_source(
            'from dataclasses import dataclass, asdict\n'
            'from decimal import Decimal\n'
            '@dataclass\n'
            'class Item:\n'
            '    amount: str\n'
            'def solve(data):\n'
            '    return asdict(Item(str(Decimal(data) + Decimal("0.2"))))\n',
            '0.1')
        self.assertEqual(result, {'ok': True, 'value': {'amount': '0.3'}})

    def test_external_file_remains_unreadable(self):
        outside = self.root / 'outside.txt'
        outside.write_text('fixture-only')
        result = self.run_source(
            'def solve(data):\n'
            f'    return open({json.dumps(str(outside))}).read()\n')
        self.assertFalse(result['ok'])
        self.assertEqual(result['error'], 'PermissionError')

    def test_project_file_remains_read_only(self):
        target = self.project / 'protected.txt'
        target.write_text('original')
        result = self.run_source(
            'def solve(data):\n'
            f'    with open({json.dumps(str(target))}, "w") as stream:\n'
            '        stream.write("changed")\n'
            '    return True\n')
        self.assertFalse(result['ok'])
        self.assertEqual(result['error'], 'PermissionError')
        self.assertEqual(target.read_text(), 'original')

    def test_network_socket_remains_denied(self):
        result = self.run_source(
            'import socket\n'
            'def solve(data):\n'
            '    socket.socket()\n'
            '    return True\n')
        self.assertFalse(result['ok'])
        self.assertEqual(result['error'], 'PermissionError')

    def test_process_creation_remains_denied(self):
        result = self.run_source(
            'import os\n'
            'def solve(data):\n'
            '    return os.fork()\n')
        self.assertFalse(result['ok'])
        self.assertEqual(result['error'], 'PermissionError')
